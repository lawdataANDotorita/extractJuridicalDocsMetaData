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


            return textNew;
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
      response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {
            "role": "system",
            "content": [
              {
                "type": "text",
                "text": "אני רוצה שתנתח מסמכים משפטיים שאני אעביר לך.\nמה שאני רוצה כפלט זה את השדות הבאים בלבד: תאריך פרסום, סוג פסק דין, מזהה תיק, אזור בארץ, ערכאה, שופט/ים, צדדים בדיון: צד א' וצד ב'. וגם באי כוח, כלומר עורכי דין מייצגים אם ישנם: עורך דין לצד א' ועורך דין לצד ב'\n\nהתשובה צריכה להינתן כייצוג אובייקט json פשוט.\nעם המיפוי של השדות לכותרות הבאות:\ndate = תאריך פרסום\ntype = סוג פסק דין\ntik = מזהה תיק\narea = אזור בארץ\ncourt = ערכאה\njudge = שופט/ים\nside1 = צד א'\nside2 = צד ב'\nlawyer1 = עורך דין לצד א'\nlawyer2 = עורך דין לצד ב' \n\n אבל בלי פירמוט, בלי שורות חדשות בין השדות ובלי תווים מיותרים, רק פסיקים.\n\n\nכמה הבהרות:\nהתאריך צריך להיות בפורמט של תאריך בלבד, של DD/MM/YYYY\n\nמזהה תיק צריך להיות בפורמט אחד מתוך האפשרויות הבאות:\n1. סוג תיק שמורכב מאחת עד ארבע אותיות בעברית ויכול לכלול גם מרכאות. לאחריו רווח או רווחים ולאחר מכן מספר תיק ולאחר מכן מפריד שיכול להיות גרש או לוכסן ולאחר מכן עוד מספר\n\n\nערכאה ואזור בד\"כ יהיו צמודים אחד לשני. קודם ערכאה ואח\"כ אזור. אזור הוא עיר בארץ.\nלערכאות בית משפט עליון ובית דין ארצי לעבודה שדה האזור ריק.\nדוגמאות:\nבית משפט השלום בחיפה\nכאן הערכאה היא 'בית משפט השלום' והאזור הוא 'חיפה'\n\n\nסוג פסק דין יכול להיות 'פסק דין' או 'החלטה' או 'גזר דין' או משהו מהסוג הזה\n\nמספר הבהרות לגבי הצדדים:\n1. פעמים רבות המילה נגד או נ' מפרידה בין צד א' לצד ב' \n2. אני מבקש פרוט של כל הצדדים ולא מקסימום של שלושה צדדים\n\nלגבי הצדדים: פעמים רבות המילה נגד או נ' מפרידה בין צד א' ל-צד ב'\n\n\n\nאני לא רוצה שדות נוספים מלבד אלו שציינתי."
                }
            ]
          },
          {
            "role": "user",
            "content": [
              {
                "type": "text",
                "text":text
              }
            ]
          },
        ],
        temperature=0,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={
          "type": "json_object"
        }
      )
      answer = response.choices[0].message.content

      # Parse the JSON string into a Python dictionary
      json_data = json.loads(answer)
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

  