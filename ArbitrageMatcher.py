import json
import numpy as np
import re
from sklearn.metrics.pairwise import cosine_similarity
from anthropic import Anthropic
from datetime import datetime


class ArbitrageMatcher:
    def __init__(self, top_n, api_key):
        self.top_n = top_n
        self.client = Anthropic(api_key=api_key)
        self.matches = []
        
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

    def ask_claude(self, desc1, desc2, model):
        """Ask Claude if two bets are the same event"""
        system_prompt = """You are an expert at determining if two prediction market questions are asking about the same event. 
        Compare the two markets and respond with only "yes" or "no". 
        Ignore minor edge cases. Pro Football = Superbowl, Pro Basketball = NBA unless specified otherwise.
        The entities and outcomes must match."""

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=150,
                temperature=0,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f'Market 1: "{desc1}"\nMarket 2: "{desc2}"\n\nRespond with only "yes" or "no":'
                }]
            )
            return message.content[0].text.strip().lower() == "yes"
        except Exception as e:
            print(f"Error calling Claude: {e}")
            return False

    def check_market_for_matches(self, ticker, all_markets, all_embeddings, similarity_threshold=0.7):
        """
        Check a single market for matches on the opposite platform
        
        Returns:
            dict: match data if found, None otherwise
        """
        if ticker not in all_markets:
            return None
        
        title, desc, source = all_markets[ticker][:3]
        if source == 'polymarket':
            poly_outcomes = all_markets[ticker][3]
            poly_asset_ids = all_markets[ticker][4]
        else:
            yes_sub_title = all_markets[ticker][3]
            no_sub_title = all_markets[ticker][4]
            kalshi_title = all_markets[ticker][0]
            kalshi_ticker = ticker

        # Determine target platform
        target_source = 'kalshi' if source == 'polymarket' else 'polymarket'

        # Get top N candidates
        candidates = self.get_top_n_matches(ticker, target_source, all_markets, all_embeddings)
        
        if not candidates:
            print("  ⊘ No candidates from opposite platform")
            return None
        
        # Check similarity threshold
        best_sim = candidates[0]['similarity']
        if best_sim < similarity_threshold:
            print(f"  ⊘ SKIPPED - Best similarity {best_sim:.3f} < {similarity_threshold}")
            return None
        
        found_match = False
        match_candidate = None
        match_model = None
        
        # Try Haiku first
        for candidate in candidates:
            if candidate['similarity'] < 0.7:
                continue
            
            if self.ask_claude(desc, candidate['description'], "claude-haiku-4-5-20251001"):
                match_candidate = candidate
                match_model = 'haiku'
                print(f"  ✓ MATCH (Haiku, sim: {candidate['similarity']:.3f})")
                print(f"    {target_source.upper()}: {candidate['title']}")
                found_match = True
                break
        
        # Try Sonnet if no Haiku match
        if not found_match:
            print("  → Retrying with Sonnet...")
            for candidate in candidates:
                if candidate['similarity'] < 0.7:
                    continue
                
                if self.ask_claude(desc, candidate['description'], "claude-sonnet-4-5-20250929"):
                    match_candidate = candidate
                    match_model = 'sonnet'
                    print(f"  ✓ MATCH (Sonnet, sim: {candidate['similarity']:.3f})")
                    print(f"    {target_source.upper()}: {candidate['title']}")
                    found_match = True
                    break
        
        if not found_match:
            print("  ✗ NO MATCHES")
            return None
        
        match_ticker = match_candidate['ticker']

        if target_source == 'polymarket':
            poly_outcomes = all_markets[match_ticker][3]
            poly_asset_ids = all_markets[match_ticker][4]
        else:
            yes_sub_title = all_markets[match_ticker][3]
            no_sub_title = all_markets[match_ticker][4]
            kalshi_title = all_markets[match_ticker][0]
            kalshi_ticker = match_ticker

        poly_yes_id, poly_no_id, kalshi_ticker = self._map_polymarket_yes_no(poly_outcomes, poly_asset_ids, yes_sub_title, no_sub_title, kalshi_title, kalshi_ticker)
        print(poly_outcomes, poly_asset_ids, yes_sub_title, no_sub_title, kalshi_title, kalshi_ticker)
        return (poly_yes_id, poly_no_id, kalshi_ticker)
    
    def _map_polymarket_yes_no(self, poly_outcomes, poly_asset_ids, yes_sub_title, no_sub_title, kalshi_title, kalshi_ticker):
        poly_yes_id = None
        poly_no_id = None
        kalshi_yes_id = None
        kalshi_no_id = None

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
                no_text = norm(no_sub_title)
                full = norm(f"{kalshi_title} {kalshi_ticker}")

                def score(o):
                    v = expand_outcome(o)
                    return (
                        int(any(x in yes_text for x in v)),
                        int(any(x in no_text for x in v)),
                        int(any(x in full for x in v)),
                    )

                s0, s1 = score(poly_outcomes[0]), score(poly_outcomes[1])
                if s0 > s1:
                    poly_yes_id, poly_no_id = poly_asset_ids[0], poly_asset_ids[1]
                elif s1 > s0:
                    poly_yes_id, poly_no_id = poly_asset_ids[1], poly_asset_ids[0]
                    
        return poly_yes_id, poly_no_id, kalshi_ticker


    def save_matches(self, path="data/arbitrage_matches.json"):
        """Save matches to JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.matches, f, indent=2, ensure_ascii=False)

    def run_initial_matching(self, all_markets, all_embeddings, similarity_threshold=0.7):
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
        
        print(f"Processing {len(poly_tickers)} Polymarket markets...\n")
        
        match_count = 0
        for i, ticker in enumerate(poly_tickers):
            print(f"[{i+1}/{len(poly_tickers)}]", end=" ")
            ids = self.check_market_for_matches(
                ticker, 
                all_markets, 
                all_embeddings, 
                similarity_threshold
            )
            if ids:
                match_count += 1
                match_data = {
                    "poly_yes_token" : ids[0],
                    "poly_no_token" : ids[1],
                    "kalshi_ticker" : ids[2]
                }
                self.matches.append(match_data)
                self.save_matches()
                yield match_data
        
        print("\n" + "="*60)
        print(f"INITIAL MATCHING COMPLETE - {match_count} matches found")
        print("="*60 + "\n")

    def check_new_markets(self, all_markets, all_embeddings, similarity_threshold=0.7):
        """
        Check for any new markets since last check
        
        Yields matches as they're found
        """
        current_tickers = set(all_markets.keys())
        new_tickers = current_tickers - self.processed_tickers
        
        match_count = 0
        for ticker in new_tickers:
            # Only process if embedding is ready
            if ticker in all_embeddings:
                ids = self.check_market_for_matches(
                    ticker,
                    all_markets,
                    all_embeddings,
                    similarity_threshold
                )
                if ids:
                    match_count += 1
                    match_data = {
                        "poly_yes_token": ids[0],
                        "poly_no_token": ids[1],
                        "kalshi_ticker": ids[2]
                    }
                    self.matches.append(match_data)
                    self.save_matches()
                    yield match_data
                self.processed_tickers.add(ticker)
        
        if new_tickers:
            print(f"Checked {len(new_tickers)} new markets, found {match_count} matches")