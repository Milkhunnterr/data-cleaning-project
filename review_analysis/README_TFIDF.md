# การสกัด Clean และเสนอคำ/วลีด้วย TF-IDF

งานวิเคราะห์อยู่ใน package `review_analysis` ภายใน repository เดิม และแบ่งเป็น
4 ขั้น: สกัดข้อความจาก ZIP/XLSX, Clean ด้วยฟังก์ชันเดิมจาก `main.py` ที่ root,
เสนอ unigram/bigram ด้วย TF-IDF และจัดกลุ่มคำ/วลีตามความหมายเพื่อให้มนุษย์
ตรวจและตั้งชื่อ Aspect ภายหลัง ไม่มี sentiment classification และโปรแกรมไม่ตั้งชื่อ
Aspect อัตโนมัติ

## ติดตั้ง dependency

รันจาก root ของ repository:

```bash
python -m pip install -r review_analysis/requirements-tfidf.txt
```

## โครงสร้างและคำสั่งรัน

```text
data/                              # ZIP / Excel ต้นฉบับ
main.py                            # ฟังก์ชัน Detect / Clean เดิม
review_analysis/
├── extract_text.py
├── run_cleaning.py
├── analyze_tfidf.py
├── cluster_terms.py
├── requirements-tfidf.txt
└── outputs/                       # ผลลัพธ์ที่สร้าง ไม่ติดตามด้วย Git
```

ไฟล์ต้นฉบับอยู่ใน `data/` และผลลัพธ์ทั้งหมดอยู่ใน
`review_analysis/outputs/` ซึ่งสคริปต์จะสร้างให้อัตโนมัติเมื่อจำเป็น

```bash
python -m review_analysis.extract_text --input-dir ./data --output ./review_analysis/outputs/data.json
python -m review_analysis.run_cleaning --input ./review_analysis/outputs/data.json --output ./review_analysis/outputs/cleaned_data.json
python -m review_analysis.analyze_tfidf --input ./review_analysis/outputs/cleaned_data.json --output ./review_analysis/outputs/tfidf_aspect_candidates.csv
python -m review_analysis.cluster_terms --input ./review_analysis/outputs/tfidf_aspect_candidates.csv --output ./review_analysis/outputs/term_clusters.xlsx
```

path ที่ผู้ใช้ระบุแบบ relative จะอ้างจาก working directory จึงควรรันคำสั่งข้างต้น
จาก root ของ repository ส่วนค่า default ของแต่ละสคริปต์อ้างจากตำแหน่ง package
ด้วย `pathlib`

ค่าเริ่มต้นคือ `min_df=2`, แสดง 50 อันดับแรกใน Terminal และเรียงตามจำนวน
รีวิวที่พบจากมากไปน้อย หากเท่ากันจึงเรียงด้วยคะแนน TF-IDF รวม ผลลัพธ์ทุก
feature ที่ผ่าน `min_df` จะถูกสร้างจากผลวิเคราะห์ชุดเดียวกันและไม่จำกัดเพียง
50 รายการ:

- `tfidf_aspect_candidates.csv` รวม unigram และ bigram ใช้ UTF-8 BOM
- `tfidf_aspect_candidates.xlsx` แยกชีต `Unigram` และ `Bigram` แต่รักษาอันดับ
  เดิมจากผลรวม

ก่อนเริ่มกรอกคอลัมน์แง่มุมหรือหมายเหตุใน Excel ควร **Save As เป็นชื่ออื่น**
เพราะการรันสคริปต์ครั้งถัดไปจะเขียนทับไฟล์ผลลัพธ์ชื่อเดิม

ตัวอย่างการปรับค่า:

```bash
python -m review_analysis.analyze_tfidf --min-df 3 --top-n 100
python -m review_analysis.analyze_tfidf --sort-by tfidf
python -m review_analysis.analyze_tfidf --input ./review_analysis/outputs/cleaned_data.json --output ./review_analysis/outputs/candidates.csv
```

เมื่อกำหนด `--output ./review_analysis/outputs/candidates.csv` โปรแกรมจะสร้าง
`candidates.csv` และ `candidates.xlsx` ในตำแหน่งเดียวกัน

ดูตัวเลือกทั้งหมดด้วย `python -m review_analysis.analyze_tfidf --help`
รายการ stopwords ใช้ `set(pythainlp.corpus.thai_stopwords())` โดยตรง
ไม่รวมไฟล์หรือรายการยกเว้นเพิ่มเติม จึงไม่มีตัวเลือก `--stopwords`
โปรแกรมแสดงรุ่น PyThaiNLP, จำนวน stopwords ทั้งหมด, สถานะของคำ
`ไม่`, `ราคา`, `วิว`, `บริการ`, `สะอาด` ในรายการ library และคำที่
พบและคัดออกจริงพร้อมความถี่ใน Terminal

## การเตรียม token และ bigram

ใช้ PyThaiNLP `word_tokenize` กับ `engine="newmm"` ซึ่งเป็นตัวตัดคำแบบอาศัย
พจนานุกรม และแสดงตัวอย่าง token จากข้อมูลจริงก่อนแสดงอันดับ ช่องว่างธรรมดา
ไม่ตัดความต่อเนื่องของ bigram จึงรองรับ `วิว สวย` แต่ newline, เครื่องหมาย,
อีโมจิ, ตัวเลขล้วน, `[URL]`, `[PHONE]` และ stopword จะตัดความต่อเนื่อง จึงไม่
สร้าง bigram ข้ามคำที่ถูกกรองหรือข้ามประโยค

โค้ดชุดนี้ทดสอบกับ PyThaiNLP 5.4.0 หากเปลี่ยนเวอร์ชันหรือพจนานุกรมของตัวตัดคำ
ควรตรวจตัวอย่าง token ที่โปรแกรมแสดงอีกครั้ง เพราะผลการตัดคำอาจเปลี่ยนได้

การกรองทำเฉพาะ token สำเนาสำหรับวิเคราะห์ ข้อความต้นฉบับยังใช้ในรีวิวตัวอย่าง
โดยอ้างตำแหน่ง Input ซึ่งเริ่มนับจาก 1 ตัวอย่างถูกเลือกจาก feature ที่พบใน token
จริงและไม่ใช้ substring search

## การคำนวณ

กำหนดให้ `N` คือจำนวนรีวิว และ `df(t)` คือจำนวนรีวิวที่พบ feature `t`:

```text
idf(t) = log((1 + N) / (1 + df(t))) + 1
tfidf(t, d) = count(t, d) * idf(t)
TFIDFSum(t) = ผลรวม tfidf(t, d) ของทุกรีวิว
```

พารามิเตอร์เทียบเท่ากับ `smooth_idf=True`, `sublinear_tf=False`, `norm=None`
โดย `norm=None` ไม่ปรับน้ำหนักตามความยาวรีวิว ดังนั้นรีวิวยาวหรือคำที่กล่าวซ้ำ
อาจมีอิทธิพลมากขึ้น

- จำนวนครั้งที่พบ คือจำนวน occurrence รวม
- จำนวนรีวิวที่พบ คือ document frequency ซึ่งหนึ่งรีวิวนับไม่เกินหนึ่งครั้ง
- คะแนน TF-IDF รวม คือน้ำหนัก TF-IDF รวม ไม่ใช่ค่าความถี่เดียวกัน

โปรแกรมตรวจและรายงานข้อความซ้ำแบบตรงกันทุกตัวอักษรก่อนวิเคราะห์ แต่ไม่ลบหรือ
เปลี่ยนข้อมูลซ้ำ

## ขอบเขตของแนวคิดอ้างอิง

Chu et al. (2022) ใช้คำสำคัญจาก TF-IDF ประกอบการกำหนดหมวด งานนี้รับแนวคิด
การเสนอคำสำคัญก่อนมาใช้ แต่กระบวนการให้ผู้ตรวจพิจารณาบริบทและจัดกลุ่มเองเป็น
การออกแบบของงานนี้ ไม่ได้อ้างว่า Paper อธิบายผู้จัดกลุ่มหรือขั้นตอน manual ไว้
อย่างชัดเจน และไม่ได้บังคับให้ใช้ 26 คำหรือ 10 หมวดตาม Paper

SETAR (2023) ทดลอง TF-IDF แบบ unigram, bigram และทั้งสองร่วมกันเพื่อสร้าง
คุณลักษณะสำหรับจำแนก sentiment งานนี้ประยุกต์เฉพาะการทดลองคำเดี่ยวและวลีเพื่อ
เสนอ candidate ไม่ได้อ้างว่า SETAR ใช้ TF-IDF ค้นหา Aspect

หลังผู้ตรวจยืนยันคำและกลุ่มแล้ว การนับรายกลุ่มในขั้นถัดไปควรนับจำนวนรีวิวที่พบ
อย่างน้อยหนึ่งคำในกลุ่ม โดยหนึ่งรีวิวนับครั้งเดียวต่อกลุ่ม ไม่ใช่บวก document
frequency ของทุกคำ และคำกำกวมยังต้องตรวจบริบทก่อนยืนยัน Aspect

## การจัดกลุ่มคำ/วลีตามความหมาย

ติดตั้ง dependency ด้วยคำสั่งเดียวกับขั้น TF-IDF แล้วรันจาก root ของ repository:

```bash
python -m pip install -r review_analysis/requirements-tfidf.txt
python -m review_analysis.cluster_terms --input ./review_analysis/outputs/tfidf_aspect_candidates.csv --output ./review_analysis/outputs/term_clusters.xlsx
```

สคริปต์อ่านคอลัมน์ `คำ/วลี` และ `ประเภท` โดยตรง ใช้ unigram และ bigram ร่วมกัน
แต่เก็บข้อความและแถวต้นทางของแต่ละรายการไว้ตรวจความครบถ้วน คะแนน TF-IDF ไม่ได้
ถูกใช้เป็น feature สำหรับ clustering เพราะคะแนนใกล้กันไม่ได้แปลว่าความหมายใกล้กัน
และไม่มีรายการ Aspect หรือ keyword ล่วงหน้ามาบังคับผล

โมเดลเริ่มต้นคือ
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ผ่าน
Sentence Transformers 5.1.1 เป็นโมเดล 384 มิติที่รองรับภาษาไทยและหลายภาษา
โดย pin revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` เป็นค่าเริ่มต้น
ขนาดดาวน์โหลดใน cache ประมาณ 470 MB การดาวน์โหลดเกิดเฉพาะครั้งแรก CPU ใช้ได้
แต่ช้ากว่า ส่วน `--device auto` จะเลือก CUDA เมื่อ PyTorch มองเห็น GPU

เวกเตอร์ถูกทำ L2 normalization แล้วจัดกลุ่มด้วย HDBSCAN จาก scikit-learn 1.7.2
บน Euclidean distance ซึ่งสัมพันธ์กับ cosine distance โดยตรงบนเวกเตอร์ normalized
HDBSCAN เหมาะกับงานนี้เพราะไม่ต้องกำหนดจำนวนกลุ่มล่วงหน้า และทิ้งจุดที่ความหนาแน่น
ไม่พอเป็น noise ได้ จุดเหล่านี้จะอยู่ในกลุ่ม `รอตรวจสอบ` ไม่ถูกลบอย่างเงียบ ๆ

ค่าเริ่มต้นที่ใช้กับข้อมูลชุดนี้คือ `min_cluster_size=2`, `min_samples=1`,
`cluster_selection_method=eom`, `cluster_selection_epsilon=0.0`,
`min_membership_probability=0.0`, `seed=42` และ `batch_size=64` จำนวนกลุ่มจึง
เกิดจากความหนาแน่นของ embedding ไม่ได้บังคับให้ตรงกับจำนวน Aspect ที่คาดไว้
`min_cluster_size=2` กำหนดว่ากลุ่มปกติต้องมีอย่างน้อย 2 รายการ และ `eom` เลือก
กลุ่มจากความคงอยู่โดยรวม ซึ่งอาจได้กลุ่มใหญ่กว่า `leaf`; ยังเลือกทดลอง `leaf`
ได้ด้วย `--cluster-selection-method leaf` ส่วน `min_samples=1` ลดความเข้มงวด
ของ core point แต่ยังคงคำที่ไม่อยู่ในบริเวณหนาแน่นเป็น noise ค่า seed ถูกตั้งให้
ขั้น embedding ทำซ้ำได้; HDBSCAN ชุดนี้ไม่มีการสุ่ม

ปรับเกณฑ์และทรัพยากรได้ เช่น:

```bash
python -m review_analysis.cluster_terms --min-cluster-size 5 --min-samples 3
python -m review_analysis.cluster_terms --min-membership-probability 0.25 --device cpu --batch-size 32
python -m review_analysis.cluster_terms --model-revision REVISION_อื่น
python -m review_analysis.cluster_terms --help
```

ค่าที่เข้มงวดขึ้นมักทำให้ `รอตรวจสอบ` ใหญ่ขึ้น โปรแกรมพิมพ์ชื่อ/รุ่นโมเดล,
เวอร์ชันไลบรารี, device, seed และพารามิเตอร์ทั้งหมดใน Terminal ทุกครั้ง Output มี
ไฟล์เดียวคือ `review_analysis/outputs/term_clusters.xlsx` มีชีตเดียว `กลุ่มคำ`
คอลัมน์ชื่อแง่มุมและหมายเหตุเว้นว่างเสมอ โปรแกรมตรวจจำนวน Input เท่ากับสมาชิก
ทุกกลุ่ม และจะหยุดโดยไม่ตัดข้อความหากสมาชิกกลุ่มใดเกิน 32,767 ตัวอักษรต่อเซลล์
ของ Excel กรณีนั้นรูปแบบที่เก็บครบคือรายละเอียดหนึ่งคำ/วลีต่อแถว ซึ่งต้องตกลง
เปลี่ยนข้อกำหนดก่อนใช้งาน

ข้อจำกัดสำคัญคือ embedding ของคำหรือวลีสั้นไม่มีบริบทจากรีวิว คำเดี่ยวกำกวม เช่น
`น้ำ` อาจหมายถึงน้ำดื่ม น้ำทะเล หรือน้ำตก และอาจถูกจัดใกล้ความหมายที่ไม่ตรงกับ
บริบทจริง unigram ยังอาจเป็นคำทั่วไป ส่วน bigram ให้บริบทเพิ่มแต่ยังไม่เท่าประโยค
คะแนนหรือความแน่นของ clustering วัดโครงสร้างเวกเตอร์ ไม่ได้พิสูจน์ว่ากลุ่มเป็น
Aspect ที่ถูกต้อง จึงต้องตรวจทั้งกลุ่มที่สอดคล้องและกลุ่มที่ปะปนก่อนกรอกชื่อใน
คอลัมน์ D


## การทดลอง POS สี่โหมด

รันจาก repository root (คำสั่งบรรทัดเดียว ใช้ใน PowerShell ได้):

```powershell
python -m review_analysis.run_pos_experiments --mode all
python -m review_analysis.run_pos_experiments --mode noun_verb
python -m review_analysis.run_pos_experiments --mode remove_adj_adv_conj
python -m review_analysis.run_pos_experiments --mode noun_verb_adj
```

เลือก baseline อย่างเดียวด้วย `--mode baseline`; ตัวเลือกที่ใช้ร่วมกันทุกโหมดคือ
`--input`, `--min-df` (2), `--sort-by` (document_frequency), `--device` (auto)
และ `--token-examples` (2 รีวิวแรก; 0 ปิดตัวอย่าง) คำสั่งเดิมของ
`analyze_tfidf` และ `cluster_terms` ยังใช้ได้เหมือนเดิม

| โหมด | กฎบน token ที่ผ่านตัวกรองเดิม |
|---|---|
| baseline (0) | ไม่ใช้ POS ตัด feature |
| noun_verb (1) | NOUN, PROPN, VERB |
| remove_adj_adv_conj (2) | ตัด ADJ, ADV, CCONJ, SCONJ เก็บ tag อื่น |
| noun_verb_adj (3) | NOUN, PROPN, VERB, ADJ |

PROPN นับเป็นหมวดนาม; AUX ไม่ใช่ VERB ในกฎทั้งสองแบบที่อนุญาตกริยา
tag ที่ไม่รู้จัก (รวม None/ว่าง/X) จะถูกตัดในแบบ 1/3 แต่เก็บในแบบ 2
ตามหลักตัดเฉพาะสี่ tag ที่ระบุ ไม่มีการเดาความหมายหรือเพิ่มกฎเฉพาะคำ

### วิธีระบุ POS และ mapping

ทดสอบด้วย PyThaiNLP **5.4.0**, `engine="perceptron"`, `corpus="orchid_ud"`
ใช้โมเดล ORCHID ที่มากับ library และการแปลง Universal POS ของ library โดยตรง
แหล่งตรวจสอบ: [API ของ PyThaiNLP 5.4.0](https://pythainlp.org/docs/5.4.0/api/tag.html)
และ source `pythainlp/tag/orchid.py` ของ library ที่ติดตั้ง
ตารางต่อไปนี้ถอดจาก `pythainlp.tag.orchid.TO_UD` ในรุ่นที่ติดตั้ง:

| ORCHID tag | Universal POS |
|---|---|
| NCMN, NTTL, CNIT, CLTV, CMTR, CFQC, CVBL | NOUN |
| NPRP | PROPN |
| VACT, VSTA | VERB |
| NONM, **VATT**, DONM | **ADJ** |
| ADVN, ADVI, ADVP, ADVS | ADV |
| INT | INTJ |
| PPRS, PDMN, PNTR | PRON |
| DDAN, DDAC, DDBQ, DDAQ, DIAC, DIBQ, DIAQ | DET |
| NCNM, NLBL, DCNM | NUM |
| XVBM, XVAM, XVMM, XVBB, XVAE | AUX |
| RPRE | ADP |
| JCRG | CCONJ |
| PREL, JSBR, JCMP | SCONJ |
| FIXN, FIXV, EAFF, EITT, AITT, NEG | PART |
| PUNC | PUNCT |

ตารางของ library มี identity mapping สำหรับ NOUN, PROPN, ADJ, ADV, PRON,
DET, NUM, AUX, ADP, CCONJ, SCONJ, PART, PUNCT และค่าว่างไปค่าว่างด้วย
`orchid_ud` มีข้อยกเว้นภายใน library ให้ `การ`/`ความ` เป็น NOUN ซึ่งใช้ตาม
library โดยไม่ได้เพิ่มข้อยกเว้นเอง (ทั้งสองคำยังถูก stopwords กรอง)
ไม่มี `startswith("V")`: VATT ต้องเข้าสู่ ADJ จึงถูกตัดในแบบ 1/2 และผ่านแบบ 3
หาก library เปลี่ยน token หรือไม่สามารถ map tag ได้ runner หยุดพร้อมข้อผิดพลาด
แทนการเลื่อน token หรือแต่ง mapping เพิ่ม

ใช้ token จาก `tokenize_review` เดิม (newmm) ทั้งรีวิว รวมช่องว่าง วรรคตอน
newline และ placeholder เพื่อระบุ POS ในบริบทก่อนกรอง จากนั้นตรวจข้อความ ลำดับ
และจำนวน token ที่ tagger คืนมาตรงกับ input ทุกตำแหน่ง คำเดียวกันต่างบริบท
จึงอาจผ่านเฉพาะบาง occurrence; จำนวนครั้ง df และรีวิวตัวอย่างคำนวณจาก
occurrence ที่ผ่านจริง ข้อความตัวอย่างยังเป็นรีวิวเต็มตามต้นฉบับ

ฟังก์ชันกลางใน `analyze_tfidf.py` อ่านข้อมูล สร้าง features คำนวณ/เรียง TF-IDF
เลือกตัวอย่างและส่งออก ส่วน `pos_rules.py` ระบุกฎแต่ละแบบอย่างชัดเจน
runner ตัดคำและ tag ร่วมครั้งเดียว แต่ baseline ไม่ใช้ POS ในการตัดสิน feature
ทุกโหมดใช้ `set(thai_stopwords())` โดยตรงและ N เท่ากับจำนวนรีวิวทั้งหมด
แม้รีวิวบางรายการไม่เหลือ features; อันดับเริ่มใหม่ภายในแต่ละโหมด

ลำดับเหตุผลการตัดใช้ตัวกรองเดิมก่อน แล้วใช้ POS เฉพาะ usable tokens
Terminal รายงาน stopword occurrences และ POS-only occurrences แยกกัน
แจกแจง POS-only ตาม tag จึงไม่มีการนับ occurrence เดียวซ้ำในสองยอดนี้
ช่องว่างธรรมดาข้ามได้ตามกฎเดิม แต่ stopword, token ที่ POS ตัด, newline,
placeholder, ตัวเลขและสัญลักษณ์เป็น boundary จึงไม่จับคู่คำสองข้างใหม่
ตัวอย่าง token/POS และ bigram ใน Terminal ใช้ Input index เดียวกันทุกโหมด
และแสดงสถานะก่อนใช้ min_df (bigram ที่ผ่าน POS อาจไม่ผ่าน min_df ภายหลัง)

Clustering ใช้ default จาก `cluster_terms.parse_args([])` ร่วมกันทุกโหมดและ
ตรึงวิธีเลือกกลุ่มเป็น EOM: โมเดล/revision, L2 normalization, Euclidean metric,
min_cluster_size=2, min_samples=1, epsilon=0, membership threshold=0,
seed=42, batch_size=64 เหมือนเดิม ไม่มี embedding cache ระหว่างการทดลอง
candidate ว่างจะได้ตารางหัวคอลัมน์อย่างเดียว; candidate น้อยกว่า 2 จะอยู่
รอตรวจสอบทั้งหมดโดยข้าม embedding/HDBSCAN และแจ้งตรง ๆ ไม่มีการสร้างกลุ่มปกติปลอม

### Output และการตรวจเปรียบเทียบ

ทุกครั้งเขียนลง `review_analysis/outputs/{mode}/` โดยตรง โดย mode คือ
`baseline`, `noun_verb`, `remove_adj_adv_conj`, `noun_verb_adj`
แต่ละโฟลเดอร์มี `{mode}_tfidf.csv`, `{mode}_tfidf.xlsx`, `{mode}_cluster.xlsx`
เช่น `noun_verb_tfidf.csv`, `noun_verb_tfidf.xlsx`, `noun_verb_cluster.xlsx`
ใช้ตัวส่งออกและรูปแบบเดิมทั้งหมด รวมชีต สี และช่องผู้ตรวจที่ว่าง
รันซ้ำจะเขียนทับไฟล์ชื่อเดิม: **ควร Save As เป็นไฟล์ชื่ออื่นก่อนกรอกแง่มุมหรือหมายเหตุเอง**
เพราะผลใหม่จะล้างข้อมูลผู้ตรวจในไฟล์ผลลัพธ์ชื่อเดิม
`--mode all` ส่งออกครบ 4 โหมด; โหมดเดียวเขียนเฉพาะ 3 ไฟล์ของโหมดนั้น
clustering อ่าน CSV ที่เพิ่งส่งออกของโหมดเดียวกัน (เมื่อไม่มี candidate จะส่งออกกลุ่มว่าง)
ไม่มีการสร้างโฟลเดอร์รอบใหม่ timestamp random suffix หรือสำรองอัตโนมัติ
ไม่แก้ `data.json`, `cleaned_data.json` หรือไฟล์ผลรุ่นก่อนที่อยู่ตรงใต้ outputs
โฟลเดอร์เก่า `before_pythainlp_eom_*` และ `pos_run_*` ไม่ถูกใช้งานหรือถูกลบโดย runner
ผลลัพธ์ยังอยู่ใต้ outputs ซึ่ง Git ignore และไม่สร้างไฟล์รายงานหรือ log เพิ่มอัตโนมัติ

Terminal สรุป unigram/bigram/candidates, กลุ่มปกติ, จำนวน/สัดส่วนรอตรวจสอบ
และ POS-only occurrences แยก tag; เมื่อไม่มี candidate สัดส่วนจะแสดง N/A
โปรแกรมแสดงกลุ่มจริงขนาดใหญ่เพื่อให้ตรวจ ไม่มีการตั้งชื่อ Aspect อัตโนมัติ
การประเมินควรดูทั้งกลุ่มที่สอดคล้อง กลุ่มปะปน และบริบทที่ tag ผิด:
โมเดล ORCHID มาจากข้อความวิชาการ ซึ่งอาจต่างจากรีวิวท่องเที่ยว
จำนวนคำหรือ noise ที่น้อยลงจึงไม่ได้แปลว่าคุณภาพดีที่สุดโดยอัตโนมัติ
การทดลองนี้ตรึง EOM ทุกโหมด จึงเปรียบเทียบผลของกฎ POS ภายใต้ tagger เดียวกันได้

รันชุดทดสอบทั้งหมด:

```powershell
python -m pytest review_analysis -q
```


### ผลรันจริงจาก cleaned_data.json จำนวน 1,231 รีวิว

ตรวจ baseline CSV เท่ากับผลล่าสุดเดิมทุก byte และ clustering เท่ากันทั้ง
รหัสกลุ่ม ลำดับสมาชิก และจำนวนสมาชิก (974 กลุ่มปกติ + รอตรวจสอบ)
ตรวจ CSV กับ Excel และสมาชิก clustering ครบทั้ง 4 โหมด/12 ไฟล์
รูปแบบสีและช่องผู้ตรวจว่างตรงข้อกำหนด ผลชุดนี้อยู่ในโฟลเดอร์ชื่อโหมดโดยตรง

| mode | unigram | bigram | candidates | กลุ่มปกติ | รอตรวจสอบ | สัดส่วน | POS-only occurrences |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 2,736 | 2,113 | 4,849 | 974 | 1,828 | 37.70% | 0 |
| noun_verb | 2,528 | 1,628 | 4,156 | 828 | 1,582 | 38.07% | 5,019 |
| remove_adj_adv_conj | 2,585 | 1,750 | 4,335 | 866 | 1,636 | 37.74% | 3,796 |
| noun_verb_adj | 2,599 | 1,850 | 4,449 | 893 | 1,693 | 38.05% | 2,516 |

ทุกโหมดกรอง stopword 32,317 occurrences เท่ากัน (รวม ๆ/ฯ ที่อยู่ใน library
และถูกตรวจ stopword ก่อน symbol ตามโค้ดเดิม) ยอด POS ต่อไปนี้ไม่นับซ้ำยอดนั้น:

| tag | noun_verb | remove_adj_adv_conj | noun_verb_adj |
|---|---:|---:|---:|
| ADJ | 2503 | 2503 | 0 |
| ADP | 379 | 0 | 379 |
| ADV | 911 | 911 | 911 |
| AUX | 236 | 0 | 236 |
| CCONJ | 33 | 33 | 33 |
| DET | 250 | 0 | 250 |
| NUM | 141 | 0 | 141 |
| PART | 44 | 0 | 44 |
| PRON | 167 | 0 | 167 |
| PUNCT | 6 | 0 | 6 |
| SCONJ | 349 | 349 | 349 |

ตัวอย่างจริง Input 2: “เป็นหาดที่สวยงามเหมาะแก่การมาเที่ยววันหยุดพักผ่อนกับครอบครัว
เม็ดทรายละเอียด มีกอจกรรมทางน้ำให้เล่นมากมาย” (ในไฟล์เป็นบรรทัดเดียว)
ได้ `หาด/NOUN`, `สวยงาม/ADJ`, `เหมาะ/VERB`, `เล่น/VERB`:
แบบ 1/2 ตัด occurrence สวยงาม ส่วน baseline/แบบ 3 เก็บ
bigram `สวยงาม เหมาะ` จึงผ่านขั้น token ใน baseline/แบบ 3 และถูกปฏิเสธในแบบ 1/2
ทุกแบบยังเก็บ `เที่ยว วันหยุด`; `หาด สวยงาม` ไม่ถูกสร้างข้าม `ที่` ที่เป็น stopword

ตัวอย่างกลุ่มสอดคล้อง: กลุ่มทะเล 10 รายการเหมือนกันใน baseline G19,
แบบ 1 G13, แบบ 2 G16, แบบ 3 G15 ได้แก่ ทะเล, น้ำทะเล, ริมทะเล, ทะเลใน,
ท้องทะเล, ชม ทะเล, ฝั่งทะเล, ทะเล ฝั่ง, ทางทะเล, มหาสมุทร
ตัวอย่างปะปน: G01 ทุกโหมดยังรวม `หาดใหญ่` กับ `หาด`, `ชายหาด` และวลีไม่สมบูรณ์
เช่น `บาท หาด`, `หาด ทราบ` (baseline/แบบ 3 มี 36 สมาชิก; แบบ 1/2 มี 35)
แสดงว่าตัวกรอง POS ยังแก้ความกำกวมของชื่อสถานที่และการตัดคำไม่ได้ทั้งหมด

ความคลาดเคลื่อนที่ต้องตรวจ: Input 1 tagger ให้ `ซ่อน/SCONJ` และ `เงียบสงบ/NOUN`
จึงตัดซ่อนในทุกแบบ POS และเก็บเงียบสงบในทุกแบบ แม้ผู้อ่านอาจมองชนิดคำต่างออกไป
ผลเหล่านี้ใช้ตาม tagger จริง ไม่มีการแก้ tag ด้วยรายการคำพิเศษ
ดังนั้นยังไม่ควรเลือกแบบ 1 เพียงเพราะ candidates/noise เชิงจำนวนลดลง:
สัดส่วนรอตรวจสอบของแบบ 1 กลับสูงกว่า baseline และยังต้องตรวจบริบทด้วยมนุษย์
