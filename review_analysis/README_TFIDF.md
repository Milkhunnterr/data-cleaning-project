# การสกัด Clean และเสนอคำ/วลีด้วย TF-IDF

งานวิเคราะห์อยู่ใน package `review_analysis` ภายใน repository เดิม และแบ่งเป็น
3 ขั้น: สกัดข้อความจาก ZIP/XLSX, Clean ด้วยฟังก์ชันเดิมจาก `main.py` ที่ root,
และเสนอ unigram/bigram ด้วย TF-IDF เพื่อให้มนุษย์ตรวจบริบทและจัดกลุ่ม Aspect เอง
ไม่มีการจัดกลุ่มอัตโนมัติหรือ sentiment classification

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
├── tfidf_stopwords.txt
├── requirements-tfidf.txt
└── outputs/                       # ผลลัพธ์ที่สร้าง ไม่ติดตามด้วย Git
```

ไฟล์ต้นฉบับอยู่ใน `data/` และผลลัพธ์ทั้งหมดอยู่ใน
`review_analysis/outputs/` ซึ่งสคริปต์จะสร้างให้อัตโนมัติเมื่อจำเป็น

```bash
python -m review_analysis.extract_text --input-dir ./data --output ./review_analysis/outputs/data.json
python -m review_analysis.run_cleaning --input ./review_analysis/outputs/data.json --output ./review_analysis/outputs/cleaned_data.json
python -m review_analysis.analyze_tfidf --input ./review_analysis/outputs/cleaned_data.json --output ./review_analysis/outputs/tfidf_aspect_candidates.csv
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
รายการ stopwords อยู่ใน `review_analysis/tfidf_stopwords.txt` และแก้ไขได้
ทีละบรรทัด โปรแกรมจะแสดง stopwords ที่พบและคัดออกจริงพร้อมจำนวนครั้งใน Terminal

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
