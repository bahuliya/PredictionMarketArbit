# data/manual_all_markets.py
# Complete manual seed of all_markets for embedding/matching.
# Structure matches EmbeddingConversion expectations:
#   polymarket: [title, descriptor, source, outcomes, clobTokenIds, sports_flag]
#   kalshi:     [title, descriptor, source, yes_sub_title, no_sub_title]

all_markets = {
    # ---------- Polymarket (10) ----------
    "HOUSECA40-26-D": [
        "Will Democratic win the House race for CA-40?",
        "Will Democratic win the House race for CA-40? If the House member sworn in for CA-40 for the term beginning in 2027 is a member of the Democratic Party, then the market resolves to Yes.",
        "polymarket",
        ["Yes", "No"],
        ["1", "1"],   # TODO
        False
    ],
    "645439": [
        "Will Ethan Del Mastro win the 2025–2026 NHL Calder Memorial Trophy?",
        "Will Ethan Del Mastro win the 2025–2026 NHL Calder Memorial Trophy? Resolves to the player awarded the 2025–26 Calder; if not a finalist, resolves No.",
        "polymarket",
        ["Yes", "No"],
        ["2", "2"],   # TODO
        True
    ],
    "566200": [
        "Will Fulham win the 2025–26 English Premier League?",
        "Will Fulham win the 2025–26 English Premier League? Resolves Yes if Fulham are crowned champions; No otherwise; Other if season not completed by 2026-10-01.",
        "polymarket",
        ["Yes", "No"],
        ["3", "3"],   # TODO
        True
    ],
    "644184": [
        "Will Draymond Green lead the NBA in steals during the 2025–26 NBA season?",
        "Resolves to the player with the highest steals-per-game average in the 2025–26 NBA regular season (NBA qualification rules/tiebreaks apply).",
        "polymarket",
        ["Yes", "No"],
        ["4", "4"],   # TODO
        True
    ],
    "582146": [
        "Will Brighton finish in the top 4 of the EPL 2025–26 standings?",
        "Resolves Yes if Brighton finish top 4 in EPL 2025–26; otherwise No; EPL tie-breakers apply; No if season not completed by 2026-10-01.",
        "polymarket",
        ["Yes", "No"],
        ["5", "5"],   # TODO
        True
    ],
    "631003": [
        "Will the Republicans win the Wyoming Senate race in 2026?",
        "Resolves to the winner of the 2026 Wyoming U.S. Senate election (including run-offs); uses AP/Fox/NBC consensus or certification.",
        "polymarket",
        ["Yes", "No"],
        ["6", "6"],   # TODO
        False
    ],
    "559683": [
        "Will George Clooney win the 2028 Democratic presidential nomination?",
        "Resolves Yes if George Clooney wins and accepts the 2028 Democratic presidential nomination; replacement before Election Day doesn’t change resolution.",
        "polymarket",
        ["Yes", "No"],
        ["7", "7"],   # TODO
        False
    ],
    "608403": [
        "Will Discord not IPO by June 30, 2026?",
        "Resolves on Discord’s first trading-day close; if no IPO by 2026-06-30 23:59 ET, resolves to “No IPO by June 30, 2026.”",
        "polymarket",
        ["Yes", "No"],                         # adjust if bucketed
        ["8", "8"],   # TODO
        False
    ],
    "630870": [
        "Will the Democrats win the New Mexico Senate race in 2026?",
        "Resolves to winner of the 2026 New Mexico U.S. Senate election (run-offs included); uses AP/Fox/NBC consensus or certification.",
        "polymarket",
        ["Yes", "No"],
        ["9", "9"],   # TODO
        False
    ],
    "569256": [
        "Will PCC win the most seats in the 2026 Colombian Senate election?",
        "Resolves Yes if PCC wins the most seats in the 2026 Colombian Senate (2026-03-08); ties resolved alphabetically; Other if no vote by 2026-12-31.",
        "polymarket",
        ["Yes", "No"],
        ["10", "10"],   # TODO
        False
    ],

    # ---------- Kalshi candidates (5 per Polymarket) ----------
    # CA-40 House
    "KXHOUSERACE-CA04-26-D": [
        "Will Democratic win the House race for CA-04?",
        "If the House member sworn in for CA-04 for the term beginning in 2027 is a Democrat, resolves Yes. Accelerated after media consensus.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXHOUSERACE-CA20-26-D": [
        "Will Democratic win the House race for CA-20?",
        "Same structure for CA-20; accelerated after media consensus.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXHOUSERACE-CA46-26-D": [
        "Will Democratic win the House race for CA-46?",
        "Same structure for CA-46; accelerated after media consensus.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXHOUSERACE-CA24-26-D": [
        "Will Democratic win the House race for CA-24?",
        "Same structure for CA-24; accelerated after media consensus.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXHOUSERACE-CA42-26-D": [
        "Will Democratic win the House race for CA-42?",
        "Same structure for CA-42; accelerated after media consensus.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Calder Trophy
    "KXNHLCALDER-26-JLEK": [
        "Who will win Calder Memorial Trophy? (Jonathan Lekkerimaki)",
        "Resolves Yes if Lekkerimaki wins 2025-26 NHL Calder Trophy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXNHLCALDER-26-CRIT": [
        "Who will win Calder Memorial Trophy? (Calum Ritchie)",
        "Resolves Yes if Calum Ritchie wins 2025-26 NHL Calder Trophy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXNHLCALDER-26-BCAT": [
        "Who will win Calder Memorial Trophy? (Berkly Catton)",
        "Resolves Yes if Berkly Catton wins 2025-26 NHL Calder Trophy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXNHLCALDER-26-LMER": [
        "Who will win Calder Memorial Trophy? (Leevi Merilaninen)",
        "Resolves Yes if Leevi Merilaninen wins 2025-26 NHL Calder Trophy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXNHLCALDER-26-BNAD": [
        "Who will win Calder Memorial Trophy? (Bradly Nadeau)",
        "Resolves Yes if Bradly Nadeau wins 2025-26 NHL Calder Trophy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Fulham EPL win
    "KXPREMIERLEAGUE-26-FUL": [
        "Will Fulham win the English Premier League?",
        "Resolves Yes if Fulham win the EPL title.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP6-26-FUL": [
        "Will Fulham finish in the top 6 in the 2025-26 EPL season?",
        "Resolves Yes if Fulham finish top 6 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP2-26-FUL": [
        "Will Fulham finish in the top 2 in the 2025-26 EPL season?",
        "Resolves Yes if Fulham finish top 2 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXFACUP-26-FUL": [
        "Will Fulham win the FA Cup?",
        "Resolves Yes if Fulham win the FA Cup.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLRELEGATION-26-FUL": [
        "Will Fulham be relegated from EPL in 2025-26?",
        "Resolves Yes if Fulham are relegated in 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # NBA steals leader
    "KXLEADERNBASTL-26-MSMA": [
        "Will Marcus Smart lead Pro Basketball in Steals Per Game for the 2025-26 Regular Season?",
        "Resolves Yes if Marcus Smart has highest SPG (league thresholds, corrections before expiry apply).",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXLEADERNBASTL-26-ACAR": [
        "Will Alex Caruso lead Pro Basketball in Steals Per Game for the 2025-26 Regular Season?",
        "Same SPG leader rules; Caruso.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXLEADERNBASTL-26-TMUR": [
        "Will Trey Murphy III lead Pro Basketball in Steals Per Game for the 2025-26 Regular Season?",
        "Same SPG leader rules; Murphy.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXLEADERNBASTL-26-TJON": [
        "Will Tre Jones lead Pro Basketball in Steals Per Game for the 2025-26 Regular Season?",
        "Same SPG leader rules; Tre Jones.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXLEADERNBASTL-26-DWHI": [
        "Will Derrick White lead Pro Basketball in Steals Per Game for the 2025-26 Regular Season?",
        "Same SPG leader rules; Derrick White.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Brighton top-4
    "KXEPLTOP2-26-BRI": [
        "Will Brighton finish in the top 2 in the 2025-26 EPL season?",
        "Resolves Yes if Brighton finish top 2 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP6-26-BRI": [
        "Will Brighton finish in the top 6 in the 2025-26 EPL season?",
        "Resolves Yes if Brighton finish top 6 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP4-26-BRI": [
        "Which EPL teams will qualify for the Champions League? (Brighton leg)",
        "Resolves Yes if Brighton are an EPL Top 4 finisher (qualify for UCL).",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP6-26-BOU": [
        "Will Bournemouth finish in the top 6 in the 2025-26 EPL season?",
        "Resolves Yes if Bournemouth finish top 6 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXEPLTOP6-26-BUR": [
        "Will Burnley finish in the top 6 in the 2025-26 EPL season?",
        "Resolves Yes if Burnley finish top 6 in EPL 2025-26.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Wyoming Senate (GOP win)
    "KXUSINDEPENDENTCONGRESS-26NOV03": [
        "Will any independent or third-party candidate win an election in the U.S. House or Senate in 2026?",
        "Resolves Yes if any non‑Dem/Non‑GOP wins a House/Senate seat in 2026; certification-based.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXDEMCOREFOURSENATESWEEP-26NOV03": [
        "Will Democrats win the 2026 senate elections in GA, MI, NC, AND ME?",
        "Parlay: all four must be Dem wins to resolve Yes.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXSENATEWYR-26-RRAS": [
        "Will Reid Rasner be the Republican nominee for the Senate in Wyoming?",
        "Resolves Yes if Rasner wins the GOP nomination for 2026 WY Senate.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXAKSENATE-26NOV03-MPEL": [
        "Will Mary Peltola win the 2026 Alaska Senate race?",
        "Resolves Yes if Mary Peltola wins 2026 Alaska Senate.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXAKSENATE-26NOV03-RGRA": [
        "Will Richard Grayson win the 2026 Alaska Senate race?",
        "Resolves Yes if Richard Grayson wins 2026 Alaska Senate.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Clooney nomination
    "KXPRESNOMD-28-MK": [
        "Will Mark Kelly be the Democratic Presidential nominee in 2028?",
        "Resolves Yes if Mark Kelly wins and accepts the 2028 Dem nomination.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXPRESNOMD-28-HCLI": [
        "Will Hilary Clinton be the Democratic Presidential nominee in 2028?",
        "Resolves Yes if Hillary Clinton wins and accepts the 2028 Dem nomination.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXPRESNOMD-28-AOC": [
        "Will Alexandria Ocasio-Cortez be the Democratic Presidential nominee in 2028?",
        "Resolves Yes if AOC wins and accepts the 2028 Dem nomination.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXPRESELECTIONOCCUR-28": [
        "Will the 2028 presidential election occur?",
        "Resolves Yes if the 2028 U.S. presidential election occurs.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXPRESNOMD-28-BS": [
        "Will Bernie Sanders be the Democratic Presidential nominee in 2028?",
        "Resolves Yes if Bernie Sanders wins and accepts the 2028 Dem nomination.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # Discord IPO timing
    "KXIPODISCORD-26MAR01": [
        "When will Discord IPO? (before Mar 1, 2026)",
        "Resolves Yes if IPO confirmed before 2026-03-01 (S-1 effective, priced, or ticker assigned).",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXIPODISCORD-26NOV01": [
        "When will Discord IPO? (before Nov 1, 2026)",
        "Resolves Yes if IPO confirmed before 2026-11-01.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXIPODISCORD-26DEC01": [
        "When will Discord IPO? (before Dec 1, 2026)",
        "Resolves Yes if IPO confirmed before 2026-12-01.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXIPODISCORD-26JUL01": [
        "When will Discord IPO? (before Jul 1, 2026)",
        "Resolves Yes if IPO confirmed before 2026-07-01.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXIPODISCORD-26JUN01": [
        "When will Discord IPO? (before Jun 1, 2026)",
        "Resolves Yes if IPO confirmed before 2026-06-01.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],

    # New Mexico Senate (Dem win) shares Kalshi candidate set above (independent/third-party + parlay etc.)

    # PCC Colombia Senate
    "KXCOLOMBIAPARLI-26MAR08-POFU": [
        "Will Party of the U win the 2026 Colombian Chamber of Representatives election?",
        "Resolves Yes if Party of the U wins most seats in 2026 Chamber election.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXCOLOMBIAPARLI-26MAR08-LPAR": [
        "Will Liberal Party win the 2026 Colombian Chamber of Representatives election?",
        "Resolves Yes if Liberal Party wins most seats in 2026 Chamber election.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXCOLOMBIAPARLI-26MAR08-CPAR": [
        "Will Conservative Party win the 2026 Colombian Chamber of Representatives election?",
        "Resolves Yes if Conservative Party wins most seats in 2026 Chamber election.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXCOLOMBIAPARLI-26MAR08-DCEN": [
        "Will Democratic Center win the 2026 Colombian Chamber of Representatives election?",
        "Resolves Yes if Democratic Center wins most seats in 2026 Chamber election.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ],
    "KXCOLOMBIAPARLI-26MAR08-GALL": [
        "Will Green Alliance win the 2026 Colombian Chamber of Representatives election?",
        "Resolves Yes if Green Alliance wins most seats in 2026 Chamber election.",
        "kalshi", "<yes_sub>", "<no_sub>"
    ]
}

def get_all_markets():
    return all_markets
