# วิธีทำงานร่วมกัน

## 1. Clone โปรเจกต์ (ครั้งแรก)

เปลี่ยน URL และชื่อโฟลเดอร์เป็นของ repository จริง:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

อัปเดต main แล้วสร้าง branch ตามชื่อฟังก์ชันที่ได้รับ ตัวอย่างงาน HTML ใช้ `feature/html`:

```bash
git fetch origin
git switch main
git pull origin main
git switch -c feature/html
```

## 2. ก่อนเริ่มทำงานทุกครั้ง

หากมีงานแก้ค้าง ให้ commit ใน branch ของตัวเองก่อน แล้วอัปเดตตามนี้:

```bash
git fetch origin
git switch main
git pull origin main
git switch feature/html
git merge main
```

เปลี่ยน `feature/html` เป็น branch ของตัวเอง หากเกิด conflict ให้แก้ให้เรียบร้อยก่อนทำงานต่อ

งานเดิมที่ยังไม่ merge เข้า main ใช้ branch เดิมต่อได้ หาก merge เข้า main แล้วและเริ่มงานใหม่ ให้สร้าง branch ใหม่จาก main ล่าสุด

## 3. แก้ฟังก์ชันและทดสอบ

- แก้เฉพาะฟังก์ชัน Detect และ Clean ที่ได้รับมอบหมาย ไม่แก้ฟังก์ชันของเพื่อน
- Detect คืน `True` / `False` ส่วนที่ยังไม่ทำคืน `None`
- Clean คืนข้อความที่แก้แล้ว หากไม่ต้องแก้ให้คืนข้อความเดิม
- ใส่ mock ของตัวเองใน `mockdata.json` ข้าง `main.py` ตามรูปแบบนี้:

```json
[
  {
    "id": "001",
    "text": "วิวสวยมาก 😊"
  }
]
```

ใช้ ID ไม่ซ้ำกัน และก่อนส่งงานอย่าลบ mock ของเพื่อน

รันโปรแกรม:

```bash
python main.py
```

หากเครื่องใช้ `python3` ให้รัน `python3 main.py`

ดูผลที่ **`checkoutput.json`**:

- `text` = ข้อความต้นฉบับ
- `cleanText` = ข้อความหลังผ่านฟังก์ชัน Clean
- flag = ผลตรวจต้นฉบับ (`true` พบ / `false` ไม่พบ / `null` ยังไม่ได้ตรวจ)

เทียบกับเฉลยที่ตัวเองเตรียมไว้ ทั้ง flag และข้อความหลัง Clean

## 4. ส่งงานขึ้น GitHub

อยู่ใน branch ของตัวเอง ทดสอบเรียบร้อยแล้วจึง Add → Commit → Push:

```bash
git branch --show-current
git add main.py mockdata.json
git commit -m "เพิ่มฟังก์ชันตรวจและ Clean HTML"
git push -u origin feature/html
```

เปลี่ยนชื่อ branch และข้อความ commit ให้ตรงกับงาน หากมีไฟล์อื่นที่เกี่ยวข้อง ให้ `git add` เพิ่มด้วย

ครั้งถัดไปใน branch เดิมใช้ `git push` ได้เลย แล้วเปิด Pull Request เข้า `main` ให้ผู้รวมงานตรวจ **ไม่ push ตรงเข้า main**
