import json
import numpy as np
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import re
from google import genai
from google.genai import types


class ArbitrageMatcher:
    def __init__(self, top_n, api_key, gemini_batch_size, max_concurrent=20):
        self.top_n = top_n
        self.client = genai.Client(api_key=api_key)
        self.matches = []
        self.gemini_batch_size = gemini_batch_size
        self.max_concurrent = max_concurrent
        
        # Track what we've already processed
        self.processed_tickers = set()

    def get_top_n_matches(self, new_ticker, target_source, all_markets, all_embeddings):
        """Get top N similar markets from target platform"""
        if new_ticker not in all_embeddings:
            return []
        
        # Get the new market's data
        new_embedding = all_embeddings[new_ticker]
        
        if new_ticker not in all_markets:
            return []
        
        # Collect all markets from target platform
        target_tickers = []
        target_embeddings = []
        
        for ticker, market_info in all_markets.items():
            source = market_info[2]  # source is at index 2
            if source == target_source and ticker in all_embeddings:
                target_tickers.append(ticker)
                target_embeddings.append(all_embeddings[ticker])
        
        if not target_embeddings:
            return []
        
        # Calculate similarities
        target_embeddings = np.array(target_embeddings)
        new_embedding = new_embedding.reshape(1, -1)
        similarities = cosine_similarity(new_embedding, target_embeddings)[0]
        
        # Get top N
        top_indices = np.argsort(similarities)[::-1][:self.top_n]
        
        candidates = []
        for idx in top_indices:
            ticker = target_tickers[idx]
            sim = similarities[idx]
            title, desc, source = all_markets[ticker][:3]
            candidates.append({
                'ticker': ticker,
                'title': title,
                'description': desc,
                'similarity': float(sim)
            })

        return candidates

    async def call_gemini_async(self, semaphore, key_desc, candidate_desc, key, sports=False):
        if sports:
            system_prompt = """
                You are a sports betting market resolution expert. Determine whether two sports prediction markets represent the SAME underlying wager.

                Treat markets as the SAME if the core sports proposition is identical, even if platforms differ in procedural or administrative rules.

                Core elements that MUST match:
                1. Same sport and league.
                2. Same subject: same team(s) or same player (aliases and abbreviations allowed).
                3. Same wager type and metric (e.g., moneyline, spread, total, team total, anytime TD, first TD, season stat leader).
                4. Same threshold or condition (e.g., -1.5 vs -2.5 or Over 1.5 vs Over 2.5 = DIFFERENT).
                5. Same time scope: same specific game date or same season/year.

                Game identity rules:
                - For player props, the game may be implicit. If the same player, league, and game date are specified, treat as the same game even if teams are not listed.
                - For team or game bets, the teams and matchup must match.

                Ignore differences in procedural wording (resolution source, postponement handling, fair-price rules) unless they change the core outcome being measured.

                If any core element differs or is unclear, respond "no".

                Respond with ONLY the word "yes" or "no".
                """     
        else:
            system_prompt = """
                You are a betting market resolution expert. Determine if two prediction markets refer to the EXACT SAME underlying event.

                Markets must match on ALL of these factors:
                1. Same person/team/entity (NOTE: the same people, teams, and entities can be referred to with different or abbreviated names)
                2. Same specific event or outcome (note: "Super Bowl" and "Pro Football Championship" are the same event)
                3. Same time frame (e.g., 2025 vs 2026 are DIFFERENT)
                4. Same scope (e.g., "Top 8" vs "Round of 16" are DIFFERENT)
                5. Same qualifying criteria

                Examples of DIFFERENT markets:
                - "X announces run for President in 2025" vs "X runs for Democratic nomination in 2028" (different scope and timeframe)
                - "Team qualifies for Round of 16" vs "Team finishes in Top 8" (different thresholds)

                Respond with ONLY the word "yes" or "no". Nothing else.
                """     
        
        model = "gemini-3-flash-preview"
        contents = f'Market 1: "{key_desc}"\nMarket 2: "{candidate_desc}"\n\nRespond with only "yes" or "no":'
       
        async with semaphore:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0,
                    ),
                )
                raw = response.text if response.text is not None else ""
                clean = re.sub(r"[^a-z]+", "", raw.lower())
                return (key, clean == "yes")
            except Exception as e:
                print(f"Error calling Gemini API for key {key}: {e}")
                return (key, False)
                
    async def ask_gemini_async(self, requests):
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = []
        for r in requests:
            task = self.call_gemini_async(
                semaphore=semaphore,
                key_desc=r["key_desc"],
                candidate_desc=r["candidate_desc"],
                key=r["key"],
                sports=r.get("sports", False),
            )
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        return list(results)

    async def check_markets_batch(self, tickers, all_markets, all_embeddings, similarity_threshold=0.7):
        """
        Check a batch of markets for matches on the opposite platform
        Only pass in tickers - this function will determine the opposite platform internally
        
        Returns:
            dict: match data if found, None otherwise
        """
        total_ticks_matches = []
        total_ticks = len(tickers)
        print(f"Processing {total_ticks} markets...\n")

        pos = 0
        while pos < total_ticks:
            curr_batch_size = 0
            batch = {}
            pos_local = 0
            for i, ticker in enumerate(tickers[pos:], start=pos):
                pos_local += 1
                if ticker not in all_markets:
                    continue
                title = all_markets[ticker][0]
                if all_markets[ticker][2] == 'polymarket':
                    target_source = 'kalshi'
                else:                    
                    target_source = 'polymarket'

                # Get top N candidates
                candidates = self.get_top_n_matches(ticker, target_source, all_markets, all_embeddings)
                if not candidates:
                    print("  ⊘ No candidates from opposite platform")
                    continue
                best_sim = candidates[0]['similarity']
                if best_sim < similarity_threshold:
                    print(f"  ⊘ SKIPPED - Best similarity {best_sim:.3f} < {similarity_threshold}")
                    continue

                batch[ticker] = []
                for candidate in candidates:
                    candidate_ticker = candidate['ticker']
                    batch[ticker].append(candidate_ticker)

                print(f"\n[{i+1}/{total_ticks}] Added to batch: {title}")
                curr_batch_size += 1
                if curr_batch_size >= self.gemini_batch_size or pos + pos_local >= total_ticks:
                    break
            
            pos += pos_local
            if not batch:
                continue

            for i in range(self.top_n):
                requests = []
                for key, value in batch.items():
                    candidate_ticker = value[i]
                    sports = False
                    if (all_markets[key][2] == 'polymarket' and all_markets[key][5]) or (all_markets[candidate_ticker][2] == 'polymarket' and all_markets[candidate_ticker][5]):
                        sports = True
                    requests.append({
                        "key": key,
                        "key_desc": all_markets[key][1],
                        "candidate_desc": all_markets[candidate_ticker][1],
                        "sports": sports,
                    })
                
                if not requests:
                    continue

                # Call Gemini API with the async requests
                batch_results = await self.ask_gemini_async(requests)
                if batch_results: 
                    count_matches = 0
                    for key, is_match in batch_results:
                        if is_match:
                            candidates = batch[key]
                            candidate_ticker = candidates[i]

                            source = all_markets[key][2]
                            if source == 'polymarket':
                                poly_outcomes = all_markets[key][3]
                                poly_asset_ids = all_markets[key][4]
                                yes_sub_title = all_markets[candidate_ticker][3]
                                no_sub_title = all_markets[candidate_ticker][4]
                                kalshi_title = all_markets[candidate_ticker][0]
                                kalshi_ticker = candidate_ticker
                            else:
                                poly_outcomes = all_markets[candidate_ticker][3]
                                poly_asset_ids = all_markets[candidate_ticker][4]
                                yes_sub_title = all_markets[key][3]
                                no_sub_title = all_markets[key][4]
                                kalshi_title = all_markets[key][0]
                                kalshi_ticker = key

                            poly_yes_id, poly_no_id, kalshi_ticker = self._map_polymarket_yes_no(poly_outcomes, poly_asset_ids, yes_sub_title, no_sub_title, kalshi_title, kalshi_ticker)
                            total_ticks_matches.append((poly_yes_id, poly_no_id, kalshi_ticker))
                            batch.pop(key)  # Remove from batch to avoid further checks
                            count_matches += 1
                    print(f"Batch run completed with {count_matches} matches found")
                else:
                    print("Batch run completed with no matches found or an error occurred")
            
            no_match = 0
            for key, value in batch.items():
                candidates_titles = []
                for candidate_ticker in value:
                    candidates_titles.append(
                        {
                            "id": candidate_ticker,
                            "title": all_markets[candidate_ticker][0],
                            "desc": all_markets[candidate_ticker][1],
                        }
                    )

                no_match_data = {
                    all_markets[key][2]: {
                        "id": key,
                        "title": all_markets[key][0],
                        "descriptor": all_markets[key][1],
                    },
                    "candidates": candidates_titles,
                    "match": False,
                    "timestamp": datetime.now().isoformat(),
                }

                # Save failure to JSON file
                with open("./failures/matching_failures.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.append(no_match_data)
                with open("./failures/matching_failures.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                no_match += 1
            print(f"Batch completed with {no_match} no matches recorded")

        print(f"\n✓ Completed! Found {len(total_ticks_matches)} total matches")
        return total_ticks_matches
    
    def _map_polymarket_yes_no(self, poly_outcomes, poly_asset_ids, yes_sub_title, no_sub_title, kalshi_title, kalshi_ticker):
        poly_yes_id = None
        poly_no_id = None

        if len(poly_outcomes) == 2 and len(poly_asset_ids) == 2:
            def norm(s):
                s = (s or "").lower()
                s = re.sub(r"[^a-z0-9.\s+-]", " ", s)
                return re.sub(r"\s+", " ", s).strip()

            def expand_outcome(o):
                o = norm(o)
                outs = {o}
                m = re.match(r"^(o|u)\s*([0-9]+(?:\.[0-9]+)?)$", o)
                if m:
                    outs.add(("over " if m.group(1) == "o" else "under ") + m.group(2))
                return list(outs)

            o0 = norm(poly_outcomes[0])
            o1 = norm(poly_outcomes[1])

            if o0 == "yes" and o1 == "no":
                poly_yes_id, poly_no_id = poly_asset_ids[0], poly_asset_ids[1]
            elif o0 == "no" and o1 == "yes":
                poly_yes_id, poly_no_id = poly_asset_ids[1], poly_asset_ids[0]
            else:
                yes_text = norm(yes_sub_title)
                # no_text = norm(no_sub_title)
                full = norm(f"{kalshi_title} {kalshi_ticker}")

                def score(o):
                    v = expand_outcome(o)
                    return (
                        int(any(x in yes_text for x in v)),
                        int(any(x in full for x in v)),
                    )

                s0, s1 = score(poly_outcomes[0]), score(poly_outcomes[1])
                if s0 > s1:
                    poly_yes_id, poly_no_id = poly_asset_ids[0], poly_asset_ids[1]
                elif s1 > s0:
                    poly_yes_id, poly_no_id = poly_asset_ids[1], poly_asset_ids[0]
                else:
                    # Log into JSON file for manual review
                    payload = {"kalshi_ticker": kalshi_ticker, "kalshi_title": kalshi_title, "yes_sub_title": yes_sub_title, "no_sub_title": no_sub_title, "poly_outcomes": poly_outcomes, "poly_asset_ids": poly_asset_ids}
                    with open("./failures/mapping_failures.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data.append(payload)
                    with open("./failures/mapping_failures.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
        return poly_yes_id, poly_no_id, kalshi_ticker

    def save_matches(self, path="data/arbitrage_matches.json"):
        """Save matches to JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.matches, f, indent=2, ensure_ascii=False)

    async def run_initial_matching(self, all_markets, all_embeddings, similarity_threshold=0.7):
        """
        Run matching on all initial markets
        
        Yields matches as they're found
        """
        print("\n" + "="*60)
        print("INITIAL MATCHING PHASE")
        print("="*60)
        
        # Mark ALL current markets as processed first
        all_current_tickers = set(all_markets.keys())
        self.processed_tickers.update(all_current_tickers)
        
        # Get all polymarket tickers
        poly_tickers = [
            ticker for ticker, market_info in all_markets.items()
            if market_info[2] == 'polymarket'  # source is at index 2
        ]

        batch_matches = await self.check_markets_batch(
            tickers=poly_tickers,
            all_markets=all_markets,
            all_embeddings=all_embeddings,
            similarity_threshold=similarity_threshold,
        )
        match_count = 0
        for match in batch_matches:
            if match[0] and match[1] and match[2]:  # Ensure all IDs are present
                match_data = {
                    "poly_yes_token": match[0],
                    "poly_no_token": match[1],
                    "kalshi_ticker": match[2]
                }
                self.matches.append(match_data)
                self.save_matches()
                match_count += 1
                yield match_data
        
        print("\n" + "="*60)
        print(f"INITIAL MATCHING COMPLETE - {match_count} matches found")
        print("="*60 + "\n")

    async def check_new_markets(self, all_markets, all_embeddings, similarity_threshold=0.7, sports=False):
        """
        Check for any new markets since last check
        
        Yields matches as they're found
        """
        current_tickers = set(all_markets.keys())
        new_tickers = current_tickers - self.processed_tickers
        self.processed_tickers.update(new_tickers)
        
        batch_matches = await self.check_markets_batch(
            tickers=list(new_tickers),
            all_markets=all_markets,
            all_embeddings=all_embeddings,
            similarity_threshold=similarity_threshold,
        )
        match_count = 0
        for match in batch_matches:
            if match[0] and match[1] and match[2]:  # Ensure all IDs are present
                match_data = {
                    "poly_yes_token": match[0],
                    "poly_no_token": match[1],
                    "kalshi_ticker": match[2]
                }
                self.matches.append(match_data)
                self.save_matches()
                match_count += 1
                yield match_data
        
        if new_tickers:
            print(f"Checked {len(new_tickers)} new markets, found {match_count} matches")