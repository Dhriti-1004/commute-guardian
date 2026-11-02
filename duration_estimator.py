from typing import Tuple
import laya

agent = laya.load("convaiinnovations/laya")

ANCHOR_MINUTES = [30, 75, 120, 200, 300]

def estimate_event_duration(event_title : str) -> Tuple[int, int, int] :
    state = {
        "event_title" : event_title,
        "context": f"Real-world time commitment required for: {event_title}, including arrival, waiting, main activity, and wrap up."
    }
    
    questions = {
        "duration_scale": {
            "type": "score",
            "instructions": "Rate how time-consuming this activity typically is from a brief stop to an extended outing.",
            "criteria": [
                "quick stop, brief errand, or rapid transaction (under 30 to 45 minutes)",
                "short casual engagement or quick break (around 1 to 1.5 hours)",
                "standard relaxed dining, social outing, or leisure activity (around 2 hours)",
                "full-length entertainment screening, theater show, or formal session (around 3 to 3.5 hours)",
                "extended multi-stage event, half-day outing, or marathon commitment (4 to 5+ hours)"
            ]
        }
    }
    
    result = agent.predict(state, questions)
    ans = result["answers"]["duration_scale"]
    expected_level = ans["score"]
    raw_prob = ans.get("probabilities", [])
    
    if isinstance(raw_prob, dict):
        probabilities = [float(v) for v in raw_prob.values()]
    elif isinstance(raw_prob, (list, tuple)):
        probabilities = [float(v) for v in raw_prob]
    else:
        probabilities = []
    
    idx = int(expected_level)
    if idx >= len(ANCHOR_MINUTES) - 1:
        t_expected = ANCHOR_MINUTES[-1]
    else:
        fraction = expected_level - idx
        t_expected = int(round(ANCHOR_MINUTES[idx] + fraction * (ANCHOR_MINUTES[idx + 1] - ANCHOR_MINUTES[idx])))
        
    if probabilities:
        significant_levels = [i for i,p in enumerate(probabilities) if p >= 0.15]
        if not significant_levels:
            significant_levels = [max(0, idx - 1), min(len(ANCHOR_MINUTES) - 1, idx + 1)]
        t_min = ANCHOR_MINUTES[min(significant_levels)]
        t_max = ANCHOR_MINUTES[max(significant_levels)]
    else:
        t_min = max(20, int(round(t_expected * 0.75)))
        t_max = int(round(t_expected * 1.35))
    
    return t_min, t_expected, t_max

if __name__ == "__main__":
    test_cases = [
        "movie in theater",
        "date in restaurant",
        "shopping in mall",
        "quick grocery run"
    ]

    print(f"{'Event Title':<25} | {'Min (m)':<8} | {'Expected (m)':<12} | {'Max (m)':<8} | {'Expected (hrs)'}")
    print("-" * 75)
    for title in test_cases:
        t_min, t_exp, t_max = estimate_event_duration(title)
        hrs = t_exp / 60.0
        print(f"{title:<25} | {t_min:<8} | {t_exp:<12} | {t_max:<8} | {hrs:.1f} hrs")
