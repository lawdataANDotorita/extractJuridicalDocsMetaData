

from striprtf.striprtf import rtf_to_text
import re
import os

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

# Example usage
rtf_file_path = r"C:\Users\shay\my_projects\extractJuridicalDocsMetaData\test.rtf";
text = extract_rtf_content(rtf_file_path)
#with open("test.txt", "w") as file:
#    file.write(text);

script_dir = os.path.dirname(__file__)

# Construct the full path to apikey.txt
apikey_path = os.path.join(script_dir, 'apikey.txt')

# Open and read the API key
with open(apikey_path, 'r') as file:
    api_key = file.read().strip()


from openai import OpenAI
client = OpenAI(api_key=api_key)

response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "אני רוצה שתנתח מסמכים משפטיים שאני אעביר לך.\nמה שאני רוצה כפלט זה את השדות הבאים בלבד: תאריך פרסום, סוג פסק דין, מזהה תיק, אזור בארץ, ערכאה, שופט/ים, צדדים בדיון: צד א' וצד ב'. וגם באי כוח, כלומר עורכי דין מייצגים אם ישנם: עורך דין לצד א' ועורך דין לצד ב'\n\nהתשובות צריכות להיות תמציתיות עם כותרת לכל שדה ותוכן השדה ורווח שורה בין שדה לשדה\n\nכמה הבהרות:\nהתאריך צריך להיות בפורמט של תאריך בלבד, של DD/MM/YYYY\n\nמזהה תיק צריך להיות בפורמט אחד מתוך האפשרויות הבאות:\n1. סוג תיק שמורכב מאחת עד ארבע אותיות בעברית ויכול לכלול גם מרכאות. לאחריו רווח או רווחים ולאחר מכן מספר תיק ולאחר מכן מפריד שיכול להיות גרש או לוכסן ולאחר מכן עוד מספר\n\n\nערכאה ואזור בד\"כ יהיו צמודים אחד לשני. קודם ערכאה ואח\"כ אזור. אזור הוא עיר בארץ.\nלערכאות בית משפט עליון ובית דין ארצי לעבודה שדה האזור ריק.\nדוגמאות:\nבית משפט השלום בחיפה\nכאן הערכאה היא 'בית משפט השלום' והאזור הוא 'חיפה'\n\n\nסוג פסק דין יכול להיות 'פסק דין' או 'החלטה' או 'גזר דין' או משהו מהסוג הזה\n\nמספר הבהרות לגבי הצדדים:\n1. פעמים רבות המילה נגד או נ' מפרידה בין צד א' לצד ב' \n2. אני מבקש פרוט של כל הצדדים ולא מקסימום של שלושה צדדים\n\nלגבי הצדדים: פעמים רבות המילה נגד או נ' מפרידה בין צד א' ל-צד ב'\n\n\n\nאני לא רוצה שדות נוספים מלבד אלו שציינתי.\n\nאת הפלט תוציא בצורת מבנה ג'ייסון ואלה שמות השדות:\nתאריך פרסום, סוג פסק דין, מזהה תיק, אזור בארץ, ערכאה, שופט/ים, צדדים בדיון: צד א' וצד ב'. וגם באי כוח, כלומר עורכי דין מייצגים אם ישנם: עורך דין לצד א' ועורך דין לצד ב'\nתאריך = date\nסוג פסק דין = type\nמזהה תיק = tikID\nאזור = area\nערכאה = court\nשופט = judge\nצד א' = side1\nצד ב' = side2\n\nבא כוח צד א' = lawyer1\nבא כוח צד ב' = lawyer2\n"
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
    "type": "text"
  }
)
sAnswer = response.choices[0].message.content
print ("answer: "+sAnswer)
