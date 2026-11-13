# Trading forum post — draft 1

_For a forum where people trade Indian shares. Attach [funnel.png](funnel.png).
Check the forum's rules on links first; some want the link in a comment._

---

**Title:** Backtested 129 Nifty strategies with out-of-sample testing. 4 survived, all on collapsing Reliance group stocks

I wanted to know how many simple strategies actually beat buy-and-hold on
Indian large caps once you test them honestly, so I wrote the rules down
first and then ran it.

**Setup**

- Momentum, MACD crossover and Bollinger mean-reversion, each with a small
  parameter grid.
- The Nifty 50 **as it stood on 1 Jan 2011**, not today's list, so the
  companies that later fell out are still in. Seven have no price history
  any more (Cairn India, HDFC, IDFC, Jaiprakash Associates, Ranbaxy,
  Reliance Capital, Sterlite) and are left out. That leaves 43 stocks, 129
  pairs.
- Daily prices, Jan 2011 to Jan 2026, 0.1% cost per trade (also run at half
  and double).
- Tuned on the first 70% of each stock's history, judged on the rest, with a
  gap between them.
- "Survives" = higher Sharpe than buy-and-hold on both stretches, plus three
  luck checks: a timing test against shuffled trades, the Deflated Sharpe,
  and the probability of backtest overfitting.

**Result**

| Step | Pairs left |
|---|---|
| Tested | 129 |
| Beat buy-and-hold on the tuning years | 50 |
| Still ahead on the unseen years | 7 |
| Passed all three luck checks | 4 |

The typical pair had a Sharpe of 0.09 on its tuning years and −0.18 after.
Just holding the typical stock gave 0.59 over the same unseen years.

**The four survivors**: Reliance Communications (momentum and MACD),
Reliance Infrastructure (MACD), Reliance Power (MACD). Holding those lost
money for years, so any rule that sometimes sat in cash beat holding. Real
effect, not an edge. RCom also had 295 days with no volume, so its
unseen-years Sharpe of 3.04 isn't something anyone could have earned.

**834 settings on one stock.** I also tried 834 combinations on Reliance
Industries, chosen in advance. None beat holding it, on either stretch. The
best on the tuning years (Bollinger, 40 days, 3.0 wide) ranked 623rd of 834
on the unseen years.

**Survivorship bias went the other way from what I expected.** On today's
Nifty 50 list, buy-and-hold looks better (Sharpe 0.51 vs 0.28 on the tuning
years), because today's members are the ones that rose. That raised the bar,
and hid the collapsing stocks that produced three of the four survivors.

I also found a flaw in my own timing test (it got easier to pass as costs
rose) and re-ran it with a fairer shuffle. The same four survive.

Not advice; three textbook strategies, one period, one split, Yahoo prices.
Full write-up with every table:
https://finertia.hulage.in/writeup/nifty-50

Happy to hear where the method is wrong.
