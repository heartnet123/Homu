# Homu

AI Legal Assistant สำหรับค้นหาและตอบคำถามจากเอกสารกฎหมายแรงงานไทย โดยใช้ FastAPI + LangGraph + ChromaDB และมีหน้าเว็บ Next.js สำหรับใช้งาน

## ภาพรวม

โปรเจกต์นี้มี 2 ส่วนหลัก:

- Backend: FastAPI API สำหรับถามตอบ, จัดการเอกสาร, และสร้าง knowledge base
- Frontend: Next.js UI สำหรับ chat, อัปโหลดเอกสาร `.docx`, และ sync ข้อมูลเข้าระบบ

## คุณสมบัติหลัก

- ถามตอบกฎหมายแรงงานไทยผ่าน RAG pipeline
- รองรับการตอบแบบ streaming
- เก็บประวัติบทสนทนาเป็น thread
- อัปโหลดเอกสาร `.docx` เข้า knowledge base ได้
- sync เอกสารใหม่เข้า vector database ได้จากหน้าเว็บ

## Prerequisites

ก่อนเริ่มใช้งาน ควรมี:

- Python 3.12+ (แนะนำ)
- Node.js 20+ หรือ Bun
- OpenAI API key

## ติดตั้ง Backend

จากโฟลเดอร์รากโปรเจกต์:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

สร้างไฟล์ `.env` ที่รากโปรเจกต์ แล้วกำหนดค่าอย่างน้อยดังนี้:

```env
OPENAI_API_KEY=your-openai-api-key
DOC_PATH=data/พรบ.เเรงงาน.docx
CHROMA_DB_DIR=./chroma_database
COLLECTION_NAME=thai_labor_law
EMBED_MODEL_NAME=airesearch/WangchanX-Legal-ThaiCCL-Retriever
LLM_MODEL_NAME=gpt-5.4-mini
API_V1_PREFIX=/api/v1
TOP_K_RESULTS=3
AUTO_INIT_COLLECTION=true
```

หมายเหตุ:

- `OPENAI_API_KEY` จำเป็นสำหรับ backend
- `DOC_PATH` ชี้ไปยังไฟล์หรือโฟลเดอร์เอกสารที่ต้องการ ingest
- ถ้าใช้ frontend ตามโค้ดปัจจุบัน backend ควรรันที่ `http://localhost:8000`

## รัน Backend

โหมดพัฒนา:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

เมื่อรันสำเร็จ สามารถเช็กได้ที่:

- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- API capabilities: [http://localhost:8000/api/v1/capabilities](http://localhost:8000/api/v1/capabilities)

มี CLI แบบง่ายสำหรับถามตอบจาก terminal ด้วย:

```powershell
python .\main2.py
```

## ติดตั้ง Frontend

จากโฟลเดอร์ `frontend`:

```powershell
cd .\frontend
bun install
```

ถ้าไม่ได้ใช้ Bun สามารถใช้ npm แทนได้:

```powershell
cd .\frontend
npm install
```

## รัน Frontend

```powershell
cd .\frontend
bun dev
```

หรือ:

```powershell
cd .\frontend
npm run dev
```

จากนั้นเปิด [http://localhost:3000](http://localhost:3000)

## วิธีใช้งาน

### 1. ใช้งานหน้า Chat

1. รัน backend ที่พอร์ต `8000`
2. รัน frontend ที่พอร์ต `3000`
3. เปิดหน้าแรกที่ `http://localhost:3000`
4. พิมพ์คำถามเกี่ยวกับกฎหมายแรงงานไทยในช่อง chat

### 2. อัปโหลดเอกสารใหม่

1. เปิดหน้า `http://localhost:3000/documents`
2. อัปโหลดไฟล์ `.docx`
3. กด `Sync Knowledge Base`
4. รอระบบ index เอกสารให้เสร็จก่อนกลับไปถามคำถาม

### 3. ดูประวัติการสนทนา

- หน้า chat จะดึงรายการ thread จาก backend อัตโนมัติ
- เลือก thread เดิมเพื่อกลับไปดูข้อความก่อนหน้าได้

## API หลัก

API prefix ปัจจุบันคือ `/api/v1`

- `POST /api/v1/ask` ถามคำถามแบบ response ปกติ
- `POST /api/v1/ask/stream` ถามคำถามแบบ streaming
- `GET /api/v1/threads` ดูรายการบทสนทนา
- `GET /api/v1/threads/{thread_id}` ดูข้อความใน thread
- `GET /api/v1/documents` ดูรายการเอกสาร
- `POST /api/v1/upload` อัปโหลดไฟล์ `.docx`
- `POST /api/v1/ingest` sync เอกสารเข้า knowledge base
- `DELETE /api/v1/documents/{filename}` ลบเอกสาร
- `GET /api/v1/capabilities` ดูความสามารถและค่าตั้งต้นของระบบ

ตัวอย่าง request:

```bash
curl -X POST http://localhost:8000/api/v1/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"ลูกจ้างลาป่วยได้กี่วัน\"}"
```

## โครงสร้างโปรเจกต์แบบย่อ

```text
.
├─ app/          # FastAPI app, domain, services, RAG graph
├─ data/         # เอกสารต้นทาง
├─ chroma_database/  # vector database
├─ frontend/     # Next.js UI
├─ tests/        # backend tests
├─ main2.py      # CLI สำหรับถามตอบ
└─ requirements.txt
```

## ทดสอบ

รัน backend tests:

```powershell
python -m unittest .\tests\test_legal_rag_app.py
```

รัน lint ฝั่ง frontend:

```powershell
cd .\frontend
npm run lint
```

## ข้อควรรู้

- หน้า Settings ใน frontend เก็บค่า API key ไว้ใน browser local storage แต่ backend ยังใช้ `OPENAI_API_KEY` จากไฟล์ `.env` เป็นหลัก
- frontend ฝั่งปัจจุบันเรียก backend ที่ `http://localhost:8000` แบบ hardcoded
- เอกสารที่อัปโหลดต้องเป็น `.docx` เท่านั้น

## License

ดูรายละเอียดที่ [LICENSE](./LICENSE)
