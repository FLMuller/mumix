import re
p='build_data_sections.py'; s=open(p,encoding='utf-8').read()
def rep(old,new,count=1):
    global s
    assert old in s, old[:70]
    s=s.replace(old,new,count)
rep("sections 4 and 5.</li>","sections 6 and 7.</li>")
rep("sections 4 and 5 describes the whole set","sections 6 and 7 describes the whole set")
rep("as in section 5, and the reference used here is water","as in section 7, and the reference used here is water")
rep("of each source (whole or intense) is explained in section 7.","of each source (whole or intense) is explained in section 9.")
rep("the role: fitted in section 9, or not fitted with the reason","the role: fitted in section 10, or not fitted with the reason")
rep("the values of the section 7 table.","the values of the section 9 table.")
rep("(intense or whole, section 7). A dash","(intense or whole, section 9). A dash")
rep("-- section 7\n","-- section 9\n")
rep("The values in the section 7 table are","The values in the section 9 table are")
rep('r"""<h2>7. The data: whole tubes and intense tubes</h2>','r"""<h2>9. The data: whole tubes and intense tubes</h2>')
i=s.index("def main():")
s=s[:i]+'''def main():
    t = open(PAGE, encoding="utf8").read()
    app = build_appendix()
    i = t.index("<h2>Appendix")
    j = t.index("</main>")
    t = t[:i] + app + t[j:]
    sec9 = build_section7()
    head = "<h2>9. The data: whole tubes and intense tubes</h2>"
    assert head in t, "run restructure_v47.py first: the heading of section 9 is missing"
    a = t.index(head)
    b = t.index("<h2>10. ", a)
    t = t[:a] + sec9 + "\n" + t[b:]
    open(PAGE, "w", encoding="utf8", newline="\n").write(t)
    bad = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", t)
    print("written; control characters:", len(bad))


if __name__ == "__main__":
    main()
'''
i=s.index('<p>The radii overlap'); j=s.index('<h3>How this enters the model</h3>')
s=s[:i]+open('../zprev/new_mid.txt',encoding='utf-8').read()+s[j:]
i=s.index('<p>The fits of section 9 mix the two sets'); j=s.index('<h3>The data</h3>',i)
s=s[:i]+open('../zprev/new_fits_par.txt',encoding='utf-8').read()+s[j:]
rep("They are kept in the table and not fitted; only \(Re_c\) is fitted. They are candidates for a later outlier label.</div>","They are corrected (radius divided by 1.75, swirl multiplied by 3, A0c) and fitted.</div>")
rep("(their fits of the whole vortex; the same experiments give 5.2&ndash;7.4 for the intense tubes of Mouri et al. 2007).","(their fits of the whole vortex; the same experiments give 5.2&ndash;7.4 for the intense tubes of Mouri et al. 2007) and the swirl is biased low.")
rep("Mouri and Hori (2009) radius &times; 1/1.7 and swirl &times; 3","Mouri and Hori (2009) radius &times; 1/1.75 and swirl &times; 3")
rep("empty = every value of the row enters the fits of sections 8 and 9; <em>no</em> = none does; <em>no: &hellip;</em> = the listed values do not, the others do. Rows not included are shown for comparison.","empty = every value of the row enters the fits of section 10; <em>no</em> = none does; <em>no: &hellip;</em> = the listed values do not, the others do (the circulation and the tube Reynolds number are computed from the corrected radius and swirl, so a listed value of them is not fitted). Rows not included are shown for comparison.")
open(p,'w',encoding='utf-8').write(s)
print("patched")
