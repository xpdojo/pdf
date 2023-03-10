import asyncio
import io
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog

# PyMuPDF: A Python binding for the MuPDF 1.14.0 library
import fitz as mupdf
# Python Imaging Library (PIL)
from PIL import Image
from pypdf import PdfReader, PdfWriter
# A Python wrapper for Google Tesseract
# https://github.com/madmaze/pytesseract
from pytesseract import pytesseract, image_to_string


class App:
    def __init__(self, root):
        self.root = root
        # 창 제목
        self.root.title("PDF 유틸")

        # 창 사이즈
        width = 600
        height = 800
        self.root.geometry(f"{width}x{height}")

        # Entry 위젯에서 숫자만 입력하도록 validate 옵션 설정
        validate_cmd = root.register(self.validate_input)

        self.original_filename = tk.StringVar()

        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)

        # 페이지 입력 위젯
        label1 = tk.Label(root, text="First page")
        label1.grid(row=0, column=0)
        self.first_page_entry = tk.Entry(root, validate="key", validatecommand=(validate_cmd, '%S'))
        self.first_page_entry.grid(row=0, column=1)

        label2 = tk.Label(root, text="Last page")
        label2.grid(row=1, column=0)
        self.last_page_entry = tk.Entry(root, validate="key", validatecommand=(validate_cmd, '%S'))
        self.last_page_entry.grid(row=1, column=1)

        # 메시지 레이블
        self.message_label = tk.Label(root)
        self.message_label.grid(row=2, column=0, columnspan=2)

        # https://stackoverflow.com/a/47920128/10629432
        loop = asyncio.get_event_loop()

        # PDF 파일 열기 버튼
        button = tk.Button(root, text='Open PDF', command=lambda: self._create_thread_for_read(loop))
        button.grid(row=3, column=0, columnspan=2)

        # Undo 버튼
        undo_button = tk.Button(root, text="Undo (Ctrl + Y)", command=self.undo)
        undo_button.grid(row=4, column=0)

        # Redo 버튼
        redo_button = tk.Button(root, text="Redo (Ctrl + Z)", command=self.redo)
        redo_button.grid(row=4, column=1)

        # Text 위젯 생성
        self.text_widget = tk.Text(root)
        # text_widget.pack(side="left", fill="both", expand=True)
        self.text_widget.grid(row=5, column=0, columnspan=2, sticky="nsew")
        # https://tkdocs.com/tutorial/text.html#text-options
        self.text_widget.config(wrap="word",
                                undo=True)

        root.rowconfigure(5, weight=1)
        # Scrollbar 위젯 생성
        scrollbar = tk.Scrollbar(root)
        scrollbar.grid(row=5, column=2, sticky="ns")

        # Text 위젯과 Scrollbar 위젯 연결
        self.text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_widget.yview)

        # Write outlines 버튼
        button = tk.Button(root, text='Write outlines', command=self.write_outlines)
        button.grid(row=6, column=0, columnspan=2)

    # iterate over PDF pages
    def read_text(
            self,
            page_index: int,
            pdf_file: mupdf.fitz.Document,
            lang: str,
    ):
        """
        https://stackoverflow.com/questions/20327681/extract-images-from-pdf-using-python-pypdf2
        """
        # get the page itself
        page = pdf_file[page_index - 1]
        image_li = page.get_images()
        # printing number of images found in this page
        # page index starts from 0 hence adding 1 to its content
        if image_li:
            print(f"[+] Found a total of {len(image_li)} images in page {page_index}")
        else:
            print(f"[!] No images found on page {page_index}")
        for image_index, img in enumerate(page.get_images(), start=0):
            # get the XREF of the image
            xref = img[0]
            # extract the image bytes
            base_image = pdf_file.extract_image(xref)
            image_bytes = base_image["image"]

            # get the image extension
            # image_ext = base_image["ext"]

            # load it to PIL
            image = Image.open(io.BytesIO(image_bytes))
            # save it to local disk
            # save_path = f"image{page_index + 1}_{image_index}.{image_ext}"
            # image.save(open(save_path, "wb"))

            # image to korean text
            # https://github.com/tesseract-ocr/tessdata/blob/main/kor.traineddata
            # C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata
            txt: str = image_to_string(image, lang=lang)

            txt = (
                txt
                .strip()
                .replace("\r\n", "\n")
                .replace("\n\n", "\n")
                # .replace("\n", "\r\n")
                .replace(" ", "")
            )
            return txt

    def _create_thread_for_read(self, loop):
        # asyncio.create_task(open_file())
        thread = threading.Thread(target=self._read_until, args=(loop,))
        # To avoid memory leaks, it is recommended to set a thread as daemon.
        thread.setDaemon(True)
        thread.start()

    def _read_until(self, async_loop):
        async_loop.run_until_complete(self.async_read_file())

    async def async_read_file(self):
        # "1.0"부터 "end"까지의 범위를 delete() 메소드의 인자로 전달하여 Text 위젯의 텍스트를 삭제합니다.
        # "1.0"은 첫 번째 라인의 첫 번째 문자를 나타내며, "end"는 마지막 라인의 마지막 문자를 나타냅니다.
        self.text_widget.delete("1.0", "end")

        first_page = self.first_page_entry.get()  # entry1에서 입력된 텍스트 가져오기
        last_page = self.last_page_entry.get()  # entry2에서 입력된 텍스트 가져오기

        if first_page == "" or last_page == "":  # 두 Entry 위젯 중 하나라도 비어있는 경우
            self.message_label.config(text="Please enter text in both fields.")  # 메시지 출력
            return
        else:
            self.message_label.config(text="First Page: " + first_page + "\nLast Page: " + last_page)  # 입력된 텍스트 출력

        filetypes = (("PDF files", "*.pdf"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(filetypes=filetypes)  # 파일 대화상자를 통해 파일 선택
        self.original_filename.set(filename)
        print(self.original_filename.get())

        # Download Tesseract
        # 테서랙트(Tesseract): Open Source OCR Engine
        # https://github.com/UB-Mannheim/tesseract/wiki
        pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        await self.read(filename, first_page, last_page)

    async def read(self,
                   filename,
                   first_page,
                   last_page):
        # https://stackoverflow.com/questions/20327681/extract-images-from-pdf-using-python-pypdf2
        # file path you want to extract images from

        pdf_file: mupdf.fitz.Document = mupdf.open(filename)

        for page_index in range(int(first_page), int(last_page) + 1):
            content = self.read_text(page_index, pdf_file, "eng+kor")
            self.text_widget.insert("end", content)  # 파일 내용을 Text 위젯에 출력

    def undo(self):
        self.text_widget.edit_undo()  # 이전 명령 취소

    def redo(self):
        self.text_widget.edit_redo()  # 이전 명령 다시 실행

    def validate_input(self, input):
        if input == "":  # 입력된 값이 비어있는 경우
            return True
        elif input.isdigit():  # 입력된 값이 숫자인 경우
            return True
        else:
            return False

    def write_outlines(self):
        # Page를 추출할 PDF
        path = self.original_filename.get()
        pdf_reader: PdfReader = PdfReader(path)

        # Outline(구 bookmark)을 저장할 PDF
        pdf_writer: PdfWriter = PdfWriter()
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

        lines = self.text_widget.get('1.0', tk.END).split('\n')
        # 마지막 빈 줄 제거
        if lines[-1] == '':
            lines = lines[:-1]

        # Text 파일을 읽어서 PDF Outline으로 추가한다.
        default_page = 1
        for line in lines:
            strip_line = line.strip()
            if strip_line == '':
                continue

            pdf_writer.add_outline_item(title=strip_line, page_number=default_page)

        output_path = f"{path.replace('.pdf', '')}.outline.pdf"
        print(f"Write to {output_path}")
        pdf_writer.write(output_path)

        if platform.system() == 'Windows':
            # if os.name == "nt":
            print(platform.version())
            version = platform.win32_ver()
            print("Windows version:", version[0])
            print("Build number:", version[1])
            print("Service pack:", version[2])
            subprocess.Popen(["start", "", output_path], shell=True)
        elif platform.system() == "Darwin":
            print(platform.version())
            subprocess.Popen(["open", "-a", "Preview", output_path])
        elif platform.system() == "Linux":
            print(platform.version())
            subprocess.Popen(["xdg-open", output_path])
        else:
            print("Unsupported OS")


if __name__ == "__main__":
    top_level_widget = tk.Tk()

    app = App(top_level_widget)

    top_level_widget.mainloop()
