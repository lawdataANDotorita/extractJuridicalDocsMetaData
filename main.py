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
import msvcrt

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

def read_key():
  print("Press any key to continue...")
  msvcrt.getch()


try:
  script_dir = get_script_dir()

  # Construct the full path to apikey.txt
  apikey_path = os.path.join(script_dir, 'apikey.txt')

  # Open and read the API key
  with open(apikey_path, 'r') as file:
      api_key = file.read().strip()


  prmopt_path=os.path.join(script_dir, 'prompt.txt')
  with open(prmopt_path, 'r', encoding='utf-8') as file:
    prompt = file.read().strip()
  

  client = OpenAI(api_key=api_key)

  samples_dir=os.path.join(script_dir, 'docs_samples')
  corrupted_files_dir=os.path.join(script_dir, 'corrupted_files')
  # Create the corrupted_files_dir if it does not exist
  if not os.path.exists(corrupted_files_dir):
    os.makedirs(corrupted_files_dir)

  html_rows=""
  file_num=0
  for filename in os.listdir(samples_dir):
    try:
      fileoftype=False
      if filename.endswith('.xml'):
        text = read_xml(os.path.join(samples_dir, filename))
        fileoftype=True
      elif filename.endswith('.rtf'):
          text = extract_rtf_content(os.path.join(samples_dir, filename))
          fileoftype=True

      if fileoftype:
        file_num += 1
        file_name_new = f"{file_num}{os.path.splitext(filename)[1]}"
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
                  "text": prompt
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
            "type": "json_object"
          }
        )
        answer = json.loads(response.choices[0].message.content)


        json_data={"num":file_num,"date":answer["תאריך"], "type":answer["סוג פסק דין"], 
          "tik":answer["מזהה התיק"], "area":answer["אזור"], 
          "court":answer["ערכאה"], "judge":answer["שופטים"], 
          "side1":answer["צד א"], "side2":answer["צד ב"], 
          "lawyer1":answer["בא כוח צד א"], "lawyer2":answer["בא כוח צד ב"]}

        # Check if any value in json_data is a list and concatenate its elements with a column delimiter
        for key, value in json_data.items():
          if isinstance(value, list):
            json_data[key] = ', '.join(value)


        # Add the link to the current file in the json_data
        file_path = os.path.join(script_dir, filename)
        file_url = f"file:///{urllib.parse.quote(file_path.replace(os.sep, '/'))}"
        json_data["link"] = file_url

        # Create HTML table row with table data elements for each field in the JSON object
        html_rows += "<tr>"
        for key, value in json_data.items():
          if key == "link":
            html_rows += f"<td><a href='{value}'>קישור</a></td>"
          else:
            html_rows += f"<td>{value}</td>"
        html_rows += "</tr>"
        print(f"Processed file: {file_num}")
        os.rename(os.path.join(samples_dir, filename), os.path.join(samples_dir, file_name_new))
    except Exception as e:
      print(f"An error occurred inside loop: {e}. file name is - {filename}")
      # Move the corrupted file to the corrupted_files_dir

      corrupted_file_path = os.path.join(corrupted_files_dir, file_name_new)
      os.rename(os.path.join(samples_dir, filename), corrupted_file_path)
  results_template_path = os.path.join(script_dir, 'resultsTemplate.htm')

  with open(results_template_path, 'r',encoding="utf-8") as file:
    results = file.read().strip()

  # Replace *&* in results with html_rows
  results = results.replace("*&*", html_rows)

  # Save the modified results to a new HTML file
  unique_number = uuid.uuid4().int
  new_results_name = f"results_{unique_number}.htm"
  output_path = os.path.join(script_dir, new_results_name)
  with open(output_path, 'w', encoding='utf-8') as file:
    file.write(results)

except Exception as e: 
  print(f"An error occurred: {e}. file name is - {filename}");
  read_key()



  