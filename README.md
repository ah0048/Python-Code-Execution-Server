# 🛡️ Secure Python Code Execution Server  

This project provides a **secure web-based Python execution server** with sandboxing, memory limits, execution timeouts, and persistent sessions.  

👉 **Cross-platform:** Works on both **Linux & Windows**  
👉 **Session Management:** Maintain variables across executions  
👉 **Security Features:** Blocks dangerous imports (`os`, `sys`, `subprocess`, etc.)  
👉 **Execution Limits:**  
   - **Max Memory:** 100MB per session  
   - **Max Execution Time:** 2 seconds  
👉 **Web UI:** User-friendly interface for running code  

---

## 🚀 Getting Started  

### **1️⃣ Installation**  

#### **🔹 Prerequisites**  
Ensure you have **Python 3.8+** installed.  

📌 Install dependencies:  
```sh
pip install -r requirements.txt
```

#### **🔹 Install `psutil` (For Memory Monitoring)**  
```sh
pip install psutil
```

---

### **2️⃣ Running the Server**  

#### **🔹 On Linux / Mac**  
```sh
python app.py
```

#### **🔹 On Windows (Command Prompt / PowerShell)**  
```sh
python app.py
```

The server will start at:  
📌 `http://127.0.0.1:5000/`  

---

### **3️⃣ Using the Web UI**  

1️⃣ Open your browser and go to **`http://127.0.0.1:5000/`**  
2️⃣ Write Python code in the editor  
3️⃣ Click **"Execute"** to run it  
4️⃣ (Optional) Enter a **Session ID** to persist variables across executions  

---

## 🔥 API Usage (For Developers)  

### **🔹 Execute Python Code**  
📌 **Endpoint:**  
```http
POST /execute
```

📌 **Request Body (JSON):**  
```json
{
    "code": "print('Hello, World!')",
    "id": "optional-session-id"
}
```

📌 **Response Example:**  
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "stdout": "Hello, World!\n"
}
```

### **🔹 Error Handling**  
If an error occurs, the response will include an `"error"` field instead of `"stdout"` or `"stderr"`.  

Example (Timeout Exceeded):  
```json
{
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "error": "Execution timeout. Session terminated."
}
```

---

## 🔒 Security & Execution Restrictions  

This server **restricts unsafe operations** to prevent security risks.  

### **1️⃣ Blocked Modules**  
The following **dangerous modules** are **blocked**:  
🚫 `os`, `sys`, `socket`, `subprocess`, `shutil`, `pathlib`, `open`  

Example (Blocked Code):  
```python
import os
os.system("rm -rf /")  # ❌ Not Allowed!
```
📌 **Response:**  
```json
{
    "stderr": "Traceback (most recent call last):\nPermissionError: Importing 'os' is restricted.\n"
}
```

---

### **2️⃣ Execution Limits**  

| **Limit**         | **Value**  |
|------------------|-----------|
| **Max Execution Time** | 2 seconds |
| **Max Memory Usage** | 100MB |

Example (Infinite Loop):  
```python
while True: pass
```
📌 **Response:**  
```json
{
    "error": "Execution timeout. Session terminated."
}
```

Example (Exceeding Memory Limit):  
```python
a = " " * 1024 * 1024 * 200  # Allocate 200MB
```
📌 **Response:**  
```json
{
    "error": "Memory limit exceeded. Session terminated."
}
```

---

## 🛠️ Known Limitations  
🔹 **File System & Network Access Blocked**  
🔹 **No Support for Asynchronous Execution (`async` functions may not work properly)**  
🔹 **Cannot Execute Multi-Threaded Code (`threading` is blocked)**  

---

## 🛄 Submission Instructions  

📌 **Submission Email:**  
Send a ZIP file containing the project to:  
💎 `dev@namaaconsult.com`  

📌 **Email Subject Format:**  
```
{FIRST NAME} {LAST NAME} - Backend Challenge Solution
Example: Ahmed Mohamed - Backend Challenge Solution
```

📌 **ZIP File Contents:**  
```
Python-Code-Execution-Server/
├── app.py
├── templates/
│   └── index.html
├── README.md
├── requirements.txt
```

---

## ✅ Evaluation Criteria  

1️⃣ **Correctness:** Does the server execute code correctly & enforce limits?  
2️⃣ **Code Quality:** Is the code well-structured, readable, and documented?  
3️⃣ **Performance:** Does execution complete within a reasonable time?  

---

## 🎯 Summary  

- **Python Flask Server** for executing code securely  
- **Memory & Execution Time Limits** enforced  
- **Persistent Sessions** to store variables across executions  
- **Web UI for easy testing**  
- **Works on both Windows & Linux**  

💡 **Future Improvements:**  
- Add **Docker support** for stricter sandboxing  
- Implement **rate limiting** to prevent abuse  
- Support **async execution**  

🚀 **Built for secure Python execution!**  

