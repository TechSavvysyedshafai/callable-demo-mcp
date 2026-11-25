"""Gulf job-market projection 2027-2029 for an India-based insurance BA.
Inputs: IMF WEO Oct 2026 (real GDP growth), World Bank labour force 2022-2025 (SL.TLF.TOTL.IN),
salary ranges seen on JobLeads cards (Nov 2026) or labelled estimates, and a visa/access score (judgment).
Method: Monte Carlo over the Hormuz scenario and parameter uncertainty; score = 0.4 job growth + 0.3 salary + 0.3 visa ease.
"""
import random, statistics as st
random.seed(42)
N = 20000
# IMF WEO Oct 2026, real GDP % for 2027, 2028, 2029 (base case: strait reopens from March 2027)
imf = {'UAE':(7.66,6.98,5.94),'Saudi':(7.93,4.81,3.42),'Qatar':(18.76,11.15,5.47),
       'Oman':(2.22,2.49,2.89),'Kuwait':(17.12,11.51,2.33),'Bahrain':(13.94,5.15,2.90)}
gdp26 = {'UAE':-3.90,'Saudi':-3.31,'Qatar':-15.58,'Oman':4.12,'Kuwait':-16.74,'Bahrain':-11.26}
# World Bank labour force, 2022 -> 2025 compound annual growth (% / yr)
lf = {'UAE':(6499963,7602907),'Saudi':(15469059,18383677),'Qatar':(1972313,2198274),
      'Oman':(2381905,2843365),'Kuwait':(2756750,2927890),'Bahrain':(867174,919501)}
lf_cagr = {k:((b/a)**(1/3)-1)*100 for k,(a,b) in lf.items()}
# Annual salary range for BA roles, USD thousands (tax-free). seen = from JobLeads cards; est = judgment, not verified
sal = {'UAE':(49,76,'seen'),'Saudi':(32,80,'seen'),'Qatar':(41,99,'seen'),
       'Oman':(37,62,'est'),'Kuwait':(35,58,'est'),'Bahrain':(29,48,'est')}
# Visa / access for an Indian mid-level BA, 1 (hard) to 5 (easy): judgment from known policy, to be verified
visa = {'UAE':(4.5,0.3),'Saudi':(3.5,0.5),'Qatar':(3.2,0.5),'Oman':(2.3,0.5),'Kuwait':(1.8,0.4),'Bahrain':(3.8,0.4)}
# How much each economy's hiring depends on oil/gas and Hormuz (0..1): judgment
expo = {'UAE':0.35,'Saudi':0.40,'Qatar':0.85,'Oman':0.20,'Kuwait':0.90,'Bahrain':0.75}
scen = [('base',0.55),('delay',0.30),('escalate',0.15)]  # judgment: reopening as IMF assumes / ~1 year late / wider war
def pick():
    r=random.random(); c=0
    for s,p in scen:
        c+=p
        if r<c: return s
    return scen[-1][0]
countries=list(imf)
res={k:{'job':[], 'score':[], 'top':0,'first':0} for k in countries}
for _ in range(N):
    s=pick(); jobs={}; sc={}
    for k in countries:
        g=list(imf[k])
        if s=='delay': g=[g[0]*0.35, g[1]*1.15, g[2]*1.1]
        if s=='escalate': g=[gdp26[k]*0.6*expo[k]/0.5, g[1]*0.6, g[2]]
        # hiring growth: labour-force trend + elasticity x growth, damped by oil exposure (oil output adds few jobs)
        el=random.gauss(0.45,0.12)
        nonoil=[x*(1-0.6*expo[k]) for x in g]
        jg=lf_cagr[k]*random.uniform(0.6,1.0)+el*st.mean(nonoil)
        jobs[k]=jg
        lo,hi,_=sal[k]; salary=random.uniform(lo,hi)*(1 if _=='seen' else random.uniform(0.85,1.15))
        v=min(5,max(1,random.gauss(*visa[k])))
        sc[k]=(jg,salary,v)
    # normalise each dimension across countries 0..1, then weight
    def norm(i):
        vals=[sc[k][i] for k in countries]; a,b=min(vals),max(vals)
        return {k:(sc[k][i]-a)/(b-a) if b>a else 0.5 for k in countries}
    J,S,V=norm(0),norm(1),norm(2)
    tot={k:0.4*J[k]+0.3*S[k]+0.3*V[k] for k in countries}
    order=sorted(countries,key=lambda k:-tot[k])
    for k in countries:
        res[k]['job'].append(jobs[k]); res[k]['score'].append(tot[k])
    res[order[0]]['first']+=1
    for k in order[:2]: res[k]['top']+=1
def pct(xs,p): xs=sorted(xs); return xs[int(p*(len(xs)-1))]
print(f"{'Country':8} {'LF growth22-25':>14} {'Hiring growth 27-29 %/yr (p10/p50/p90)':>40} {'Salary $k':>12} {'Visa':>5} {'P(#1)':>6} {'P(top2)':>7}")
for k in sorted(countries,key=lambda k:-res[k]['first']):
    j=res[k]['job']; lo,hi,src=sal[k]
    print(f"{k:8} {lf_cagr[k]:>13.1f}% {pct(j,.1):>12.1f} / {pct(j,.5):.1f} / {pct(j,.9):.1f}{'':>14} {lo}-{hi}{'*' if src=='est' else ' ':1}  {visa[k][0]:>4} {res[k]['first']/N:>6.0%} {res[k]['top']/N:>7.0%}")
print("* salary is an estimate, not seen in listings")
