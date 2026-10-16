"""Import curated vocabulary CSV into existing topics, in one transaction."""
import argparse
import csv
import os
from pathlib import Path
from backend.app import BASE, Database


def import_csv(path,db_path=None):
    db=Database(db_path or os.getenv('LINGUA_DB',str(BASE/'data'/'lingua.sqlite3')))
    db.initialize()
    added=0
    with Path(path).open(encoding='utf-8-sig',newline='') as file, db.connect() as conn:
        reader=csv.DictReader(file)
        required={'topic_slug','term','meaning','example','level'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV cần các cột: topic_slug,term,meaning,example,level')
        for number,row in enumerate(reader,start=2):
            fields={key:(row.get(key) or '').strip() for key in required}
            if not all(fields.values()):
                raise ValueError(f'Dòng {number}: thiếu thông tin.')
            if fields['level'] not in {'A1','A2','B1','B2'}:
                raise ValueError(f'Dòng {number}: mức độ cần là A1, A2, B1 hoặc B2.')
            if len(fields['term'])>100 or len(fields['meaning'])>200 or len(fields['example'])>300:
                raise ValueError(f'Dòng {number}: nội dung vượt độ dài cho phép.')
            topic=conn.execute('SELECT id FROM topics WHERE slug=?',(fields['topic_slug'],)).fetchone()
            if not topic:
                raise ValueError(f"Dòng {number}: chủ đề '{fields['topic_slug']}' chưa tồn tại.")
            result=conn.execute('INSERT OR IGNORE INTO words(topic_id,term,meaning,example,level) VALUES(?,?,?,?,?)',
                                (topic['id'],fields['term'],fields['meaning'],fields['example'],fields['level']))
            added+=result.rowcount
    return added


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Nhập thêm bộ từ vựng CSV vào Lingua.')
    parser.add_argument('csv_file',type=Path)
    parser.add_argument('--db',type=Path)
    args=parser.parse_args()
    try:
        print(f'Đã thêm {import_csv(args.csv_file,args.db)} mục từ mới. Mục từ đã có được bỏ qua.')
    except (OSError,ValueError) as error:
        parser.exit(1,f'Lỗi: {error}\n')
