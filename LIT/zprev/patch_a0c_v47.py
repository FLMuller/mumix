p='build_data_sections.py'; s=open(p,encoding='utf-8').read()
def rep(old,new):
    global s
    assert old in s, old[:80]
    s=s.replace(old,new,1)
# (a) rows of the table
rep('''("Mouri et al. 2003, 2004, 2007 (hot wire, intense)", "none", "none",
         "A high threshold (the top 0.1&ndash;1% of the increments, 3&sigma; for 2003) favours crossings close to the axis, where the signal is largest; the authors say the radius is close to the true mean (5&ndash;7 \\(\\eta\\)). The amplitude is then about 0.9 of the peak."),''',
'''("Mouri et al. 2003, 2004, 2007 (hot wire, intense)", "none", "none; left out of the fits (2004, 2007)",
         "A high threshold (the top 0.1&ndash;1% of the increments, 3&sigma; for 2003) favours crossings close to the axis, where the signal is largest; the authors say the radius is close to the true mean (5&ndash;7 \\(\\eta\\)). They are the tails of the chord distribution of the experiments of Mouri and Hori (2009), not independent tubes, and are left out of the fits (see the last paragraph of this section)."),''')
rep('''("Mouri and Hori 2009 (hot wire, all tubes)", "&divide; 1.7", "&times; 3",''','''("Mouri and Hori 2009 (hot wire, all tubes)", "&divide; 1.75", "&times; 3",''')
# (b) the table of the cuts
i=s.index("    cut = '<div class=\"tablebox\">"); j=s.index('    text = r"""<h3>A0c.')
s=s[:i]+'''    cut = '<div class="tablebox"><table class="dt">\n<thead><tr><th>amplitude cut \\(f\\)</th><th>0.2</th><th>0.3</th><th>0.4</th><th>0.5</th><th>0.7</th><th>0.9</th></tr></thead>\n<tbody>\n' \
          '<tr><td>radius of the fit / true radius</td><td>1.92</td><td>1.61</td><td>1.45</td><td>1.37</td><td>1.23</td><td>1.15</td></tr>\n' \
          '<tr><td>swirl of the fit / true swirl</td><td>0.34</td><td>0.45</td><td>0.54</td><td>0.60</td><td>0.76</td><td>0.93</td></tr>\n' \
          '<tr><td>product (\\(Re_c\'/Re_c\\))</td><td>0.65</td><td>0.72</td><td>0.78</td><td>0.83</td><td>0.93</td><td>1.06</td></tr>\n</tbody></table></div>'
    tilt = '<div class="tablebox"><table class="dt">\n<thead><tr><th>tilt limit</th><th>20&deg;</th><th>45&deg;</th><th>70&deg;</th></tr></thead>\n<tbody>\n' \
           '<tr><td>swirl factor for a true radius of 4.97 \\(\\eta\\) (radius ratio 1.67&ndash;1.85)</td><td>2.8&ndash;3.3</td><td>2.4&ndash;2.8</td><td>2.0&ndash;2.4</td></tr>\n' \
           '<tr><td>true radius 4.5 \\(\\eta\\) (ratio 1.84&ndash;2.05)</td><td>3.2&ndash;3.9</td><td>2.7&ndash;3.4</td><td>2.4&ndash;2.9</td></tr>\n' \
           '<tr><td>true radius 5.4 \\(\\eta\\) (ratio 1.53&ndash;1.71)</td><td>2.4&ndash;2.9</td><td>2.0&ndash;2.5</td><td>1.7&ndash;2.1</td></tr>\n</tbody></table></div>'
'''+s[j:]
# (f) the lead-in of the table
rep("keeping the events whose peak is at least a fraction \\(f\\) of the central amplitude (the detection threshold relative to the strength of the tube), the means of the events that are kept are:</p>",
    "keeping the events whose peak is at least a fraction \\(f\\) of the central amplitude (the detection threshold relative to the strength of the tube), averaging the profiles of the events that are kept (aligned on their zero crossing, as Mouri and Hori average the signals centred on each tube) and fitting a Burgers profile to the mean, as they do, the radius and the swirl of the fit relative to those of the tube are (analysis script <code>fit_threshold.py</code>, 1500 events for each cut):</p>")
# (c) the paragraph after the table
i=s.index("<p>A high threshold (large \\(f\\)) keeps only near-axis crossings"); j=s.index("<p>The probe has a finite length")
s=s[:i]+'''<p>A high threshold (large \\(f\\)) keeps only near-axis crossings (ratios close to 1); an average over all tubes includes weak crossings (small \\(f\\)). The radius ratio of 1.75 that brings the 8.8 \\(\\eta\\) of Mouri and Hori (2009) to 5.0 \\(\\eta\\) corresponds to \\(f\\approx0.25\\) and to a swirl ratio of 0.40, a swirl factor of 2.5; the tilt limit and the true radius move the factor between 1.7 and 3.9:</p>
""" + tilt + r"""
<p>The product \\(Re_c'/Re_c\\) of the fit is 0.7&ndash;0.8 at these cuts, so the circulation is not conserved by the mean-profile fit. The factor 3 used is inside the range and is the value that puts the swirl on the common curve (section 10); 2.5 is also compatible with the data. Two limits of this model: it assumes identical tubes (the measured spread of radii is mostly real, lognormal with a spread of about 0.5 in \\(\\ln R\\)), and it selects events by their peak signal, whereas Mouri's cut acts on the velocity increment over a short separation, which is a slope: for a separation of 0.5 \\(R\\) the ratios at the same \\(f\\) are 1.60 and 0.45 at \\(f=0.1\\) and 1.37 and 0.57 at \\(f=0.2\\), so a radius ratio of 1.75 needs \\(f<0.1\\), the whole distribution. Checks: (i) the size distribution that Belin et al. measured with a hot film has its peak at \\(R=3.5\\,\\eta\\) and its mean near \\(6\\,\\eta\\) (read from his Fig. 5); the peak is set by near-axis crossings and corresponds to \\(r_{\\max}=5.5\\,\\eta\\), the mean divided by 1.7 gives \\(5.6\\,\\eta\\); the fit of the chord model to the whole curve (<code>fit_chord.py</code>) gives a true radius of 3.8&ndash;4.2 \\(\\eta\\) (a true \\(r_{\\max}\\) of 6&ndash;6.7 \\(\\eta\\)) for a tilt limit of 0&ndash;45&deg; and does not separate these tilt limits; (ii) Mouri and Hori state that \\(R_0\\) is above the true mean radius for all tubes but close to it for intense tubes.</p>
"""+r"""'''+s[j:]
open(p,'w',encoding='utf-8').write(s)
print("a0c part 1 patched")
