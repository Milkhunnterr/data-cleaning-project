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


## การทดลอง POS ร่วมกับ Thai WordNet สี่โหมด

ใช้ POS `perceptron/orchid_ud` บน token ของรีวิวทั้งฉบับก่อนกรอง เพื่อรักษาบริบท
ตรวจจำนวน/ข้อความ/ลำดับ token ให้ตรงกัน หากเลื่อนตำแหน่งให้หยุด ไม่จับคู่เงียบ ๆ
ใช้ Thai WordNet ผ่าน NLTK `synsets(token, lang="tha")` และรวบรวมทุก synset:
`n → NOUN`, `v → VERB`, `a/s → ADJ`, `r → ADV` ไม่เดา PROPN หรือ conjunction
cache เฉพาะ WordNet รายคำ ไม่ cache POS รายคำ เพราะคำเดิมเปลี่ยนหน้าที่ตามบริบทได้
API อ้างอิง [NLTK WordNet](https://www.nltk.org/howto/wordnet.html)

ติดตั้งทรัพยากรเพิ่มเติมครั้งแรก (ไม่ดาวน์โหลดอัตโนมัติระหว่างวิเคราะห์):

```powershell
python -m pip install -r review_analysis/requirements-tfidf.txt
python -m nltk.downloader wordnet omw-1.4
```

ใช้ NLTK 3.9.2, Princeton WordNet ผ่าน OMW 1.4 ภาษาไทย หาก corpus โหลดไม่ได้
โปรแกรมหยุดแจ้งข้อผิดพลาด ไม่ตีความว่าไม่พบคำทุกคำ

| สถานะราย occurrence | หลักฐาน | เข้า candidates หลัก |
|---|---|---|
| ยืนยันร่วมกัน | POS อยู่ในชุดชนิดคำจากทุก synset รวมกรณีหลายชนิด | ต้องผ่านกฎโหมดอีกชั้น |
| ขัดแย้ง/เทียบป้ายไม่ได้ | WordNet พบคำแต่ไม่สนับสนุนป้าย POS | ไม่ผ่าน |
| มีเฉพาะผล POS | POS ทราบชนิด แต่ WordNet ไม่พบ | ไม่ผ่าน |
| ไม่ทราบชนิดคำ | POS เป็น X/ไม่ทราบ/ป้ายผิดรูปแบบ | ไม่ผ่าน |

- `baseline`: ไม่กรอง POS/WordNet และไม่โหลดทั้งสองทรัพยากรเมื่อรันเดี่ยว
- `noun_verb`: ยืนยันร่วมกันและเป็น NOUN/VERB; PROPN ไม่เท่ากับ NOUN โดยอัตโนมัติ
- `noun_verb_adj`: ยืนยันร่วมกันและเป็น NOUN/VERB/ADJ
- `remove_adj_adv_conj`: ตัด ADJ/ADV/CCONJ/SCONJ ตาม POS; ที่เหลือต้องยืนยันร่วมกัน
  เนื่องจาก WordNet mapping ครอบคลุมเพียง NOUN/VERB/ADJ/ADV จึงเหลือ NOUN/VERB
  และผลอาจเหมือน noun_verb ไม่แต่งกฎให้โหมดต่างกัน

คง tokenizer, stopwords, min_df=2, สูตร TF-IDF และ N ของรีวิวทั้งหมด
แม้รีวิวไม่เหลือ feature ก็ยังอยู่ใน N; unigram ผ่านจริงใน occurrence นั้น
bigram ใช้กฎ adjacency เดิม (ช่องว่างธรรมดาโปร่งใส) ทั้งสอง occurrence ต้องผ่าน
ไม่เชื่อมข้าม token ที่ถูกกรอง ไม่เปลี่ยนข้อความรีวิวหรือรีวิวตัวอย่าง
ไม่มีการแก้สะกด รวมเศษคำ หรือกำหนด Aspect

### Output และคำสั่ง

คง `outputs/{mode}/{mode}_tfidf.csv`, `{mode}_tfidf.xlsx`, `{mode}_cluster.xlsx`
ทั้งสี่โหมด และ `outputs/merged_clusters/{mode}_merged.xlsx` ตามเดิม
เพิ่มเพียง `outputs/pos_wordnet_review.xlsx` หนึ่งชีต: หนึ่งแถวต่อ occurrence
ที่ผ่านตัวกรองพื้นฐาน (ไม่ใช่ stopword/เครื่องหมาย/placeholder ฯลฯ)
เก็บทั้งผ่าน/ไม่ผ่าน พร้อม Input index เริ่ม 1, ข้อความ Input ไม่ดัดแปลง,
ตำแหน่ง token ก่อนกรองเริ่ม 1, token, POS, WordNet, สถานะ, flags ทั้งสามโหมด และเหตุผล
Input ค่าเริ่มต้นอ้างถึง `review_analysis/outputs/cleaned_data.json` ไม่ใช่ข้อมูลก่อน Clean
ถ้าใช้ `--input` อื่น เลข Input อ้างถึงไฟล์ที่ระบุจริงและแสดงเส้นทางใน Terminal

รัน non-baseline โหมดเดียวก็อัปเดต audit ของทั้ง Input เพื่อเทียบ flags ทั้งสามโหมด
แต่ไม่แก้ TF-IDF/clustering/merged ของโหมดอื่น; baseline เดี่ยวไม่แตะ audit เดิม
ไม่มีชีต “สรุปการรัน” ใน Excel ที่สร้างใหม่ทุกส่วน; สรุปพารามิเตอร์และจำนวนแสดง Terminal
ไม่ไล่ลบชีตในไฟล์เก่าหรือไฟล์ที่มนุษย์แก้ ไม่สร้างรายงานเสริม timestamp หรือ backups
**ปิด Excel ก่อนรัน และ Save As ก่อนกรอกแง่มุมเอง เพราะรันซ้ำทับชื่อเดิม**
กรณีไม่มี candidates เขียน CSV/header และ Excel ว่างใหม่; candidates ไม่พอ clustering
เก็บทั้งหมดเป็นรอตรวจสอบ ไม่ทิ้งไฟล์เก่าให้เหมือนผลใหม่

PowerShell จาก repository root (แต่ละคำสั่งหนึ่งบรรทัด; merging ทำต่อเมื่อรอบแรกสำเร็จ):

```powershell
python -m review_analysis.run_pos_experiments --mode all --token-examples 0; if ($LASTEXITCODE -eq 0) { python -m review_analysis.merge_clusters --mode all --distance-threshold 0.25 }
python -m review_analysis.run_pos_experiments --mode noun_verb --token-examples 0; if ($LASTEXITCODE -eq 0) { python -m review_analysis.merge_clusters --mode noun_verb --distance-threshold 0.25 }
python -m pytest review_analysis -q
```

### ข้อจำกัดการตีความ

การเห็นตรงกันไม่รับประกันความถูกต้อง POS อาจผิดและ WordNet ไม่ได้เลือกความหมายตามบริบท
การไม่พบ WordNet ไม่แปลว่าคำผิด/ไม่มีความหมาย ชื่อสถานที่ ภาษาพูด คำประกอบ
และชนิดคำที่ lexicon ไม่ครอบคลุมอาจถูกกันออก การบังคับยืนยันทำให้ recall ลดลง
รายงานสัดส่วนทั้ง occurrence และคำไม่ซ้ำแยกกัน: คำเดียวอาจอยู่หลายสถานะในต่างบริบท
จึงไม่ควรรวมร้อยละของคำไม่ซ้ำ จำนวนคำลดลงไม่ใช่หลักฐานว่าคุณภาพดีขึ้น

### ผลจริงล่าสุด: WordNet + POS (27 ตุลาคม 2026)

รัน Input 1,231 รีวิวด้วยค่าเดิม min_df=2, EOM, embedding/revision/L2 เดิม
และ complete/cosine distance_threshold=0.25; ไม่มีโหมดใดว่างหรือเล็กจน cluster ไม่ได้

| mode | unigram | bigram | candidates | กลุ่มรอบแรก | กลุ่มหลัง merge | รอตรวจสอบ |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 2736 | 2113 | 4849 | 974 | 425 | 1828 |
| noun_verb | 1189 | 510 | 1699 | 354 | 224 | 599 |
| remove_adj_adv_conj | 1189 | 510 | 1699 | 354 | 224 | 599 |
| noun_verb_adj | 1235 | 613 | 1848 | 379 | 235 | 663 |

baseline CSV SHA256 ก่อน/หลังตรงกัน:
`4096eab1cbf87b9519a6a237745a306f4dc5d4f147a576f36dc6c7710ef982bc`
ตรวจ data.json/cleaned_data.json ไม่เปลี่ยน และ checksum clustering Input ก่อน/หลัง merging ตรงกันทุกโหมด
สมาชิกครบ 4849/1699/1699/1848 รวม noise; กลุ่มเดิมที่ยังเดี่ยว 205/145/145/147 ตามลำดับ
ช่องชื่อ Aspect/หมายเหตุยังว่างทั้งหมด ไม่โยก noise เข้ากลุ่ม

จาก 37,960 occurrences ที่ผ่านตัวกรองพื้นฐาน และ 5,176 คำไม่ซ้ำ:

| สถานะ | occurrences | ร้อยละ | คำไม่ซ้ำ | ร้อยละของ 5176 คำ |
|---|---:|---:|---:|---:|
| ยืนยันร่วมกัน | 21285 | 56.07 | 2025 | 39.12 |
| ขัดแย้ง/เทียบป้ายไม่ได้ | 5706 | 15.03 | 1009 | 19.49 |
| มีเฉพาะผล POS | 10969 | 28.90 | 2730 | 52.74 |
| ไม่ทราบชนิดคำ | 0 | 0.00 | 0 | 0.00 |

คอลัมน์คำไม่ซ้ำทับซ้อนข้ามสถานะได้ ไม่ใช่ partition ของคำไม่ซ้ำ

ผลคำที่ตรวจ (ไม่มีข้อยกเว้นเฉพาะคำ):

- อร่อย: WordNet=ADV; POS NOUN 67, VERB 28, ADJ 4, ADV 3, DET 1, AUX 1
  ยืนยันร่วมกันเพียง 3/104 occurrences แต่ ADV ไม่ผ่านทั้งสามโหมด
- สะอาด: WordNet=ADJ; POS ADJ 23, NOUN 37, ADV 12, VERB 2, PROPN 1, NUM 1
  23/76 occurrences ผ่านเฉพาะ noun_verb_adj
- ความสะอาด: WordNet ไม่พบ; POS NOUN 15 occurrences จึงอยู่ audit ไม่เข้า candidates หลัก
- ร้าน: WordNet=NOUN; POS NOUN 179 occurrences ยืนยันร่วมกันทั้งหมด
- นะคะ: WordNet ไม่พบ; POS NOUN 38, ADV 19, VERB 3, DET 2, SCONJ 1 รวม 63 occurrences

ตัวอย่างข้อความ Input ตามจริงแบบเต็ม (ลำดับอ้างถึง cleaned_data.json):

- Input 564, อร่อย, POS=NOUN / WordNet=ADV, ขัดแย้ง:
  “ตลาดน้ำสองศาสนา มีอาหารอิสลาม อร่อย ๆ ให้เลือกทานอย่างหลากหลาย”
- Input 719, สะอาด, POS=NUM / WordNet=ADJ, ขัดแย้ง:
  “บนเกาะมีสถานที่ให้ไปมากมาย สวยงาม คนไม่เยอะมากเหมือนเกาะอื่นๆ สะอาด คนบนเกาะ อัธยาศัยดีมาก”
- Input 627, ความสะอาด, POS=NOUN / WordNet ไม่พบ:
  “หาดยังคงดูสกปรกเหมือนเดิม แม้จะมีการรณรงค์เรื่องวิวทิวทัศน์และความสะอาดแล้วก็ตาม แม่ค้าก็ยังคงขายของแพงมาก”
- Input 278, ร้าน, POS=NOUN / WordNet=NOUN, ยืนยันร่วมกัน:
  “หาดทรายยาว ร้านขายของตลอดริมชายหาดมีมากมายให้เลือกสรร แต่น้ำทะเลสีไม่ค่อยสวยแล้วเสื่อมสภาพตามกาลเวลา”
- Input 184, นะคะ, POS=NOUN / WordNet ไม่พบ:
  “ใครไปเที่ยวสงขลาอย่าลืมแวะถ่ายรูปที่นี่นะคะ น้ำทะเลไม่ใสมากแต่ก็ไม่ได้สกปรกค่ะ จอดรถได้ตามริมฟุตบาทเลย”

ตัวอย่างกลุ่มหลัง merge จาก noun_verb_adj:

- M070 รวม G98/G119: “ใส”, “ใส ไหล”, “ใส เหมาะ”, “สะอาด”, “สวย สะอาด”, “ใส สะอาด”
  มีแกนเรื่องความใส/สะอาด แต่ยังมีวลีที่ต้องอ่านบริบทก่อนยืนยัน Aspect
- M027 รวม G16/G256: ราคา/ค่าใช้จ่าย/ค่าธรรมเนียม/ค่าบริการเป็นแกนสอดคล้อง
  แต่มี “อ่าว ค่าบริการ” ซึ่งยังต้องตรวจ
- M001 รวม 19 กลุ่มเดิม 52 คำ/วลี ยังปะปน “อุดหนุน”, “อาศัย”, “บังกะโล”,
  “เศียร”, “วัด”, “กม.”, “บาท”, “มอร์ ไซ” ฯลฯ: WordNet + POS ไม่ได้แก้ความผิดพลาด
  tokenizer หรือรับประกันกลุ่มความหมาย รวมถึงความผิดพลาดรอบแรกที่ติดมารอบสอง

## การทดลองรวมกลุ่มรอบที่สอง

รอบแรกจัดกลุ่มคำ/วลีด้วย Embedding/HDBSCAN ส่วนรอบสอง
`review_analysis/merge_clusters.py` อ่าน `outputs/{mode}/{mode}_cluster.xlsx`
จากชีต “กลุ่มคำ” ตามหัวตารางจริง กลุ่มเดิมเป็นหน่วยเดียวและไม่แยกสมาชิกภายใน
ใช้เฉพาะรหัสกลุ่มกับข้อความสมาชิก ไม่ใช้ชื่อแง่มุมหรือหมายเหตุของผู้ตรวจ
แยก “รอตรวจสอบ” ไว้เหมือนเดิมโดยไม่ encode หรือบังคับย้ายเข้ากลุ่ม

ขั้นตอนคำนวณ:

1. Encode ข้อความสมาชิกเดิมด้วยโมเดล/revision จากค่าเริ่มต้นของ
   `cluster_terms.py`: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`,
   revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, batch_size=64, seed=42
2. ทำ L2 normalization ของสมาชิกทุกเวกเตอร์ แล้วเฉลี่ยแบบให้น้ำหนักเท่ากัน
   ภายในแต่ละกลุ่ม (ไม่ใช้ความถี่ TF-IDF เป็นน้ำหนัก)
3. Normalize เวกเตอร์เฉลี่ยอีกครั้งเป็นตัวแทนของกลุ่มเดิม
4. ใช้ `AgglomerativeClustering(n_clusters=None, metric="cosine",
   linkage="complete", distance_threshold=...)` กับตัวแทนทุกกลุ่มปกติ

ตรวจ API กับ scikit-learn 1.7.2 ที่ติดตั้งแล้ว ไม่เพิ่ม dependency
[เอกสาร AgglomerativeClustering](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.AgglomerativeClustering.html)
อธิบาย complete linkage ว่าใช้ระยะห่างสูงสุดระหว่างจุดของสองชุด
ในงานนี้จุดคือ centroid ของกลุ่มเดิม ไม่ใช่สมาชิกคำทุกคู่
จึงช่วยควบคุมการรวมเป็นสาย แต่ไม่รับประกันความหมายของกลุ่มใหม่

ค่าเริ่มต้น `--distance-threshold 0.25` เป็นจุดเริ่มทดลองที่ค่อนข้างเข้มงวด
เมื่อเทียบกับช่วง cosine distance 0–2: ยอมรวมภายใต้ระยะของ centroid ต่ำกว่า 0.25
(ความคล้าย cosine มากกว่า 0.75) **ไม่ใช่ค่ามาตรฐานจาก Paper หรือค่าที่พิสูจน์
แล้วว่าเหมาะสมกับข้อมูลนี้** ลดเป็น 0.15 เพื่อรวมยากขึ้น หรือเพิ่มเป็น 0.35
เพื่อทดลองรวมง่ายขึ้น ตรวจกลุ่มจริงทุกครั้งและบันทึก threshold ที่ใช้
ค่า 0 ไม่รวมแม้เวกเตอร์เหมือนกัน เพราะ sklearn ไม่รวมที่ระยะเท่ากับ threshold
ไม่กำหนดจำนวน Aspect ปลายทาง กลุ่มเดี่ยวคงอยู่ได้ และไม่มีคำพิเศษบังคับการรวม
หาก embedding หรือ centroid เป็น zero vector จะหยุดแจ้งข้อผิดพลาด

คำสั่ง PowerShell จาก repository root แต่ละคำสั่งเป็นหนึ่งบรรทัด:

```powershell
python -m review_analysis.merge_clusters --mode all --distance-threshold 0.25
python -m review_analysis.merge_clusters --mode baseline --distance-threshold 0.25
python -m review_analysis.merge_clusters --mode noun_verb --distance-threshold 0.25
python -m review_analysis.merge_clusters --mode remove_adj_adv_conj --distance-threshold 0.25
python -m review_analysis.merge_clusters --mode noun_verb_adj --distance-threshold 0.25
```

รองรับ `--device cpu` หรือ `--device cuda` เพิ่มเติม; ค่าเริ่มต้น auto
ผลอยู่ใต้ `review_analysis/outputs/merged_clusters/`:

- `baseline_merged.xlsx`
- `noun_verb_merged.xlsx`
- `remove_adj_adv_conj_merged.xlsx`
- `noun_verb_adj_merged.xlsx`

ไม่สร้าง timestamp หรือสำรองอัตโนมัติ รันซ้ำทับเฉพาะ merged ของโหมดที่เลือก
**ปิด Excel ก่อนรัน และ Save As ก่อนกรอกแง่มุม/หมายเหตุด้วยมือ**
ตรวจไฟล์ล็อก Excel `~$...` และแจ้งกรณีระบบปฏิบัติการปฏิเสธการเขียน/สิทธิ์
โดยไม่แก้ Input รอบแรก ไม่มีไฟล์รายงานอื่น และ outputs ยังคงถูก Git ignore

ชีต “กลุ่มคำ” มี 7 คอลัมน์:
รหัสกลุ่มใหม่, รหัสกลุ่มเดิมที่นำมารวม, จำนวนกลุ่มเดิม, คำ/วลีทั้งหมดในกลุ่ม,
จำนวนคำ/วลี, ชื่อแง่มุมที่ผู้ตรวจยืนยัน, หมายเหตุผู้ตรวจ
สมาชิกและรหัสกลุ่มเดิมแยกบรรทัดในเซลล์ F/G ว่างและพื้นเหลืองอ่อน
หัวตารางน้ำเงิน ตัวอักษรขาว ข้อมูลขาว ไม่สลับสีแถว มี wrap/filter/freeze header
เรียงจำนวนสมาชิกมากไปน้อย ถ้าเท่ากันใช้ tuple ของรหัสกลุ่มเดิมเรียงตามตัวอักษร
แล้วกำหนด M001, M002, ... สมาชิกภายในคงลำดับแถว/บรรทัดต้นทาง
“รอตรวจสอบ” แยกไว้แถวสุดท้าย (จำนวนกลุ่มเดิมในแถวนี้คือ 1)
ไม่มีแถวรอตรวจสอบปลอมหาก Input ไม่มีรายการนี้

Terminal แสดงโหมด threshold วิธีระยะ/linkage โมเดล revision รุ่น library แทนชีตสรุป
device/batch/seed จำนวนกลุ่มก่อนและหลัง จำนวนกลุ่มที่ไม่รวม จำนวนสมาชิก
จำนวนรอตรวจสอบ และ SHA256 Input ก่อน/หลัง โดยไม่ตั้งชื่อ Aspect
ตรวจทุกกลุ่มเดิมปรากฏครั้งเดียว สมาชิกไม่หาย/เพิ่ม/ซ้ำและไม่แยกกลุ่ม
ตรวจจำนวน/ชื่อคอลัมน์/รหัส/สมาชิกซ้ำ/สูตรในคอลัมน์ข้อมูล และไม่ซ่อมข้อมูลเงียบ ๆ
หยุดก่อนเขียนหากเซลล์เกิน 32,767 UTF-16 units และตรวจ Excel round-trip
ก่อนแทนไฟล์ผลเดิม กรณีไม่มีกลุ่มปกติไม่ทำ clustering; กลุ่มปกติเดียวคงเป็น M001

### ผลทดลองประวัติก่อนใช้ WordNet ร่วม POS: threshold 0.25

ตารางด้านล่างเป็นผลเก่า ไม่ใช่ผลของกฎยืนยันร่วมกันล่าสุด

| mode | กลุ่มปกติรอบแรก | กลุ่มใหม่ | กลุ่มเดิมที่ยังเดี่ยว | รอตรวจสอบเดิม |
|---|---:|---:|---:|---:|
| baseline | 974 | 425 | 205 | 1,828 |
| noun_verb | 828 | 389 | 209 | 1,582 |
| remove_adj_adv_conj | 866 | 403 | 210 | 1,636 |
| noun_verb_adj | 893 | 408 | 210 | 1,693 |

ตรวจ Input SHA256 คงเดิมทั้งสี่ไฟล์ สมาชิกทั้งหมดตามลำดับโหมด
4,849 / 4,156 / 4,335 / 4,449 รายการอยู่ครบ รวมรอตรวจสอบ

ตัวอย่างจาก baseline:

- M013 รวม 9 กลุ่มเดิม มี 25 คำ/วลี เช่น “สวย”, “สวยงาม”, “งดงาม”,
  “ความสวยงาม”, “ความงดงาม”, “มีเสน่ห์” สอดคล้องด้านความงามโดยรวม
  แต่ยังต้องตรวจบริบทก่อนยืนยัน Aspect
- M001 รวม 30 กลุ่มเดิม มี 80 คำ/วลี ปะปน “วัด”, “หน้า วัด”, “พื้นบ้าน”,
  “คฤหาสน์” กับเศษคำ เช่น “ริ ส”, “จก รร”, “ใส กิ” แสดงข้อจำกัดของ
  embedding คำสั้น/ตัดคำผิด แม้ใช้ complete linkage
- M194 รวม G256/G825 มี “ร่มรื่น”, “ดู ร่มรื่น”, “สถานที่ ร่มรื่น”,
  “สถานที่ สวยงาม”, “สวยงาม บริเวณ” แต่ “บรรยากาศ ร่มรื่น” อยู่ M057
  และ “ร่มรื่น เย็นสบาย” อยู่ M049 จึงยังไม่รวมทุกวลีที่มีร่มรื่นเข้าด้วยกัน

Centroid similarity เป็นตัวช่วยจัดกลุ่ม ไม่ใช่หลักฐานว่าเป็น Aspect เดียวกัน
ความผิดพลาดรอบแรกจะติดมารอบสอง เพราะเก็บกลุ่มเดิมเป็นหน่วยเดียว
ค่าเฉลี่ยอาจซ่อนสมาชิกที่ไม่เข้าพวก และจำนวนกลุ่มที่ลดลงไม่ได้พิสูจน์ว่าคุณภาพดีขึ้น
ยังต้องให้มนุษย์ตรวจทั้งกลุ่มที่สอดคล้องและที่ปะปนก่อนตั้งชื่อ Aspect
