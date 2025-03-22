from openai import base_url

from utils import ArgumentParser

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import os

from model import OpenAIModel
from translator import PDFTranslator
from utils import ConfigLoader

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Vue 开发服务器地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]  # 添加这一行
)

# 创建上传文件保存的目录
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), target_language: str = Form(...)):
    # argument_parser = ArgumentParser()
    # args = argument_parser.parse_arguments()
    try:
        # 保存上传的文件
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        return {"error": str(e)}
    config_loader = ConfigLoader("config.yaml")

    config = config_loader.load_config()

    model_name = config['OpenAIModel']['model']
    api_key = config['OpenAIModel']['api_key']
    model_url = config['OpenAIModel']['base_url']
    model = OpenAIModel(model=model_name, api_key=api_key, base_url= model_url)

    file_format = config['common']['file_format']
    file_path = UPLOAD_DIR + "/" + file.filename
    # 实例化 PDFTranslator 类，并调用 translate_pdf() 方法
    translator = PDFTranslator(model)

    output_file_path = translator.translate_pdf(file_path, file_format, target_language)
    # 检查翻译后的文件是否存在
    if not os.path.exists(output_file_path):
        return {"error": "翻译后的文件不存在"}
    # 获取文件名
    translated_filename = os.path.basename(output_file_path)

    # 创建文件流
    def iterfile():
        with open(output_file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):  # 每次读取 1MB
                yield chunk
    print(f'翻译后的文件名：{translated_filename}')
    # 设置响应头，告诉浏览器这是一个文件下载
    headers = {
        'Content-Disposition': f'attachment; filename={translated_filename}'
    }

    # 返回文件流
    return StreamingResponse(
        iterfile(),
        media_type='application/octet-stream',
        headers=headers
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)