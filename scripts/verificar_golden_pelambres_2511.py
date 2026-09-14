#!/usr/bin/env python3
import zipfile, xml.etree.ElementTree as ET, re, sys
from collections import defaultdict
MAIN="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
def read_data(path):
    z=zipfile.ZipFile(path)
    ss=[]
    if "xl/sharedStrings.xml" in z.namelist():
        root=ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root:
            ss.append("".join((t.text or "") for t in si.iter(MAIN+"t")))
    wb=ET.fromstring(z.read("xl/workbook.xml"))
    rid={s.attrib["name"]:s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
         for s in wb.find("m:sheets",NS)}["DATA"]
    rel=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target={x.attrib["Id"]:x.attrib["Target"] for x in rel}[rid].lstrip("/")
    if not target.startswith("xl/"): target="xl/"+target
    sh=ET.fromstring(z.read(target))
    rows=[]
    for row in sh.find(MAIN+"sheetData"):
        vals=[]
        for c in row:
            typ=c.attrib.get("t"); v=c.find(MAIN+"v")
            val=None if v is None else v.text
            if typ=="s" and val is not None: val=ss[int(val)]
            vals.append(val)
        rows.append(vals)
    hdr=rows[0]
    return [dict(zip(hdr,r)) for r in rows[1:]]
def sum_case(rows):
    out=defaultdict(float)
    for r in rows:
        if r.get("RUTCliente")!="96790240-3" or r.get("Distribuidora_Conec")!="Cliente AT": continue
        if r.get("BarraF")!="QUILLOTA______220": continue
        out[r.get("RzSocSuministrador")]+=float(r.get("MWh") or 0)
    return out
expected={
"AES Andes S.A.":28740.712675,
"Alto Maipo SpA":65934.576255,
"Parque Eólico El Arrayán SpA":4585.622173,
"Conejo Solar SpA":16096.239654,
"Javiera SpA":12703.286223,
}
rows=read_data(sys.argv[1])
actual=sum_case(rows)
ok=True
for k,v in expected.items():
    if abs(actual.get(k,0)-v)>1e-9:
        ok=False; print("FAIL",k,actual.get(k),v)
if abs(sum(actual.values())-128060.43698)>1e-9:
    ok=False; print("FAIL total",sum(actual.values()))
print("PASS" if ok else "FAIL", dict(actual), sum(actual.values()))
sys.exit(0 if ok else 1)
