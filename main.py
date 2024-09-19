from striprtf.striprtf import rtf_to_text
from docx import Document
from lxml import etree
from openai import OpenAI
import win32com.client as win32
import re
import os
import json
import urllib.parse
import uuid
import sys

def read_xml(file_path):
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(file_path)
    content = doc.Content.Text
    doc.Close(False)
    word.Quit()
    return content

def read_docx(file_path):
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def extract_rtf_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            text = rtf_to_text(content)

            text=re.sub(r'[|]+', ' ', text);

            return text;
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_script_dir():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # sets the sys._MEIPASS attribute to the path of the temporary directory.
        print("Running in a PyInstaller bundle")
        print(f"os.getcwd(): {os.getcwd()}")
        return os.getcwd()
    else:
        # If the application is run as a script, use the directory of the script file.
        print("Running as a script")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"script_dir: {script_dir}")
        return script_dir

script_dir = get_script_dir()

# Construct the full path to apikey.txt
apikey_path = os.path.join(script_dir, 'apikey.txt')

# Open and read the API key
with open(apikey_path, 'r') as file:
    api_key = file.read().strip()

client = OpenAI(api_key=api_key)

html_row=""
for filename in os.listdir(script_dir):
    fileoftype=False
    if filename.endswith('.xml'):
      text = read_xml(os.path.join(script_dir, filename))
      fileoftype=True
    elif filename.endswith('.rtf'):
        text = extract_rtf_content(os.path.join(script_dir, filename))
        fileoftype=True

    if fileoftype:

      # replace word processing characters with real ones
      # Processing the text
      # Replace '\r' with '\n'
      text = re.sub(r'\r', '\n', text)

      # Remove any occurrences of '\x0b', '\x01', '\x07'
      text = re.sub(r'[\x0b\x01\x07]', '', text)

      # Optionally, you can remove multiple spaces with a single space
      text = re.sub(r' {2,}', ' ', text)

      lines = text.split('\n')
      extracted_lines = []
      end_phrases = ["פסק דין", "פסק-דין", "החלטה", "גזר-דין", "גזר דין"]
      
      for line in lines:
          extracted_lines.append(line)
          if any(phrase in line for phrase in end_phrases):
              break
      date_pattern = re.compile(r'\b\d{1,2}\W+(?:ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)\W+\d{4}\b|\b\d{2}/\d{2}/\d{4}\b')
      for i in range(len(lines) - 1, -1, -1):
          if date_pattern.search(lines[i]):
              extracted_lines.append(lines[i])
              break
      textNew = '\n'.join(extracted_lines)

      response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {
            "role": "system",
            "content": [
              {
                "type": "text",
                "text": "אני רוצה שתנתח מסמכים משפטיים שאני אעביר לך.\nמה שאני רוצה כפלט זה את השדות הבאים בלבד ובאותו סדר:\nתאריך פרסום\nסוג פסק דין\nמזהה תיק\nערכאה\nאזור בארץ\nשופט/ים\nצד א' בדיון\nצד ב' בדיון\nבא כוח צד א'\nבא כוח צד ב'\n\nכל ערך בשורה נפרדת ובלי הכותרות של השדות\n\n\nאם אין ערך לשדה, לרשום 'אין ערך' בשורה נפרדת.\nכמה הבהרות:\nהתאריך צריך להיות בפורמט של תאריך בלבד, של DD/MM/YYYY\n\nמזהה תיק = rec identifier:\nthe rec identifier component should be retrieved step by step. the first step is to retrieve the bbb part. \nthe bbb part is composed of up to 4 characters, . the characters could be either letters in hebrew or double quote character (\"). \n\nin the next phase we should retrieve the second part. the second part should contain a sequence composed of several numbers separated by either hyphen (-) or backslash(/). the rec identifier is a concatenation of the first and second parts, and between them separates a space char.\ne.g.:\nthe first part could be: א\"ג, א, ת\"פ, צפ\nthe second part could be: 122-33, 122-33-44, 122/33, 122/33-44\n\nand the entire rec identifier can look like this:\n122-33 א\"ג\n122-33 אג\n122-33-44 א\"ג\n122/33 א\"ג\n122/33-44 א\"ג\nת\"פ 45470-11-22\n\nערכאה היא בית משפט: בית משפט עליון או בית המשפט המחוזי או בית משפט השלום ועוד ועוד\nואזור הוא עיר בארץ: באר שבע או אשקלון או תל אביב או רמלה או חדרה וכ\"ו\nלערכאות בית משפט עליון ובית דין ארצי לעבודה שדה האזור ריק.\nדוגמאות:\nבית משפט השלום בחיפה\nכאן הערכאה היא 'בית משפט השלום' והאזור הוא 'חיפה'\nדוגמאות לאזור:\nבאר שבע\nחדרה\nירושלים\nתל-אביב\n\nבשדה שופט אני מבקש שם בלבד, בלי תואר: בלי רשם בכיר או נציג או שופט. רק את השם המלא.\n\nסוג פסק דין יכול להיות 'פסק דין' או 'החלטה' או 'גזר דין' או משהו מהסוג הזה\n\nמספר הבהרות לגבי הצדדים:\n1. פעמים רבות המילה נגד או נ' מפרידה בין צד א' לצד ב' \n2. אני מבקש פרוט של כל הצדדים ולא מקסימום של שלושה צדדים\n\nלגבי הצדדים: פעמים רבות המילה נגד או נ' מפרידה בין צד א' ל-צד ב'\n\nלגבי באי כוח - זה לא חייב להיות שמות של אנשים, זה יכול להיות גם שמות של מוסדות.\n\n\nאני לא רוצה שדות נוספים מלבד אלו שציינתי."
               }
            ]
          },
          {
            "role": "user",
            "content": textNew # send the text with real newline chars and not textual representations of them
          },
        ],
        temperature=0,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={
          "type": "text"
        }
      )
      answer = response.choices[0].message.content
      arAnswer = answer.split('\n')
      json_data={"date":arAnswer[0], "type":arAnswer[1], 
        "tik":arAnswer[2], "area":arAnswer[3], 
        "court":arAnswer[4], "judge":arAnswer[5], 
        "side1":arAnswer[6], "side2":arAnswer[7], 
        "lawyer1":arAnswer[8], "lawyer2":arAnswer[9]}
      
      # Add the link to the current file in the json_data
      file_path = os.path.join(script_dir, filename)
      file_url = f"file:///{urllib.parse.quote(file_path.replace(os.sep, '/'))}"
      json_data["link"] = file_url

      # Create HTML table row with table data elements for each field in the JSON object
      html_row += "<tr>"
      for key, value in json_data.items():
        if key == "link":
          html_row += f"<td><a href='{value}'>קישור</a></td>"
        else:
          html_row += f"<td>{value}</td>"
      html_row += "</tr>"

results_template_path = os.path.join(script_dir, 'resultsTemplate.htm')

with open(results_template_path, 'r',encoding="utf-8") as file:
  results = file.read().strip()

# Replace *&* in results with html_row
results = results.replace("*&*", html_row)

# Save the modified results to a new HTML file
unique_number = uuid.uuid4().int
new_results_name = f"results_{unique_number}.htm"
output_path = os.path.join(script_dir, new_results_name)
with open(output_path, 'w', encoding='utf-8') as file:
  file.write(results)

  