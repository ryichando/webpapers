# MIT License
#
# Copyright (c) 2021 Ryoichi Ando
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# モジュールのインポート
import os, sys, configparser, subprocess, unidecode, argparse
from PIL import Image
from pybtex.database import parse_file # pip3 install pybtex (https://pybtex.org/)
from shlex import quote
from PyPDF2 import PdfFileReader
#
# 目的のディレクトリを読み込む
parser = argparse.ArgumentParser()
parser.add_argument('root_dir', help='Root directory')
args = parser.parse_args()
root_dir = args.root_dir
#
# パラメータを読み込む
config = configparser.ConfigParser()
config.read('{}/config.ini'.format(root_dir))
page_title = config['DEFAULT']['page_title']
thumbnail_page_count = int(config['DEFAULT']['thumbnail_page_count'])
image_filesize_limit = int(config['DEFAULT']['image_filesize_limit'])
image_dimension_limit = int(config['DEFAULT']['image_dimension_limit'])
image_page_limit = int(config['DEFAULT']['image_page_limit'])
convert_video = config['DEFAULT']['convert_video'] == 'yes'
resource_dir = 'resources'
#
# サポートされる動画のタイプを列挙する
video_types = [ '.mp4', '.avi', '.mov', '.flv', '.mpg', '.mpeg', '.m4v' ]
video_template = """
<a href="#" style="padding-right: 0.75rem; white-space: pre;" data-toggle="modal" data-target="#modal3c-{id}">{text}</a>
<div class="modal fade" id="modal3c-{id}" tabindex="-1" role="dialog">
<div class="modal-dialog modal-lg" role="document">
<div class="modal-content">
<div class="modal-header">
<h5 class="modal-title">{text}</h5>
<button type="button" class="close" data-dismiss="modal" aria-label="Close">
<span aria-hidden="true">&times;</span>
</button>
</div>
<div class="modal-body" id="modal3c-body-{id}">
<script>
	$("#modal3c-{id}").on("show.bs.modal",function () {{
		let container = document.getElementById("modal3c-body-{id}");
		let obj = document.getElementById("my-video-{id}");
		if(typeof(obj) == 'undefined' || obj == null) {{
			let video = document.createElement('video');
			video.setAttribute('id', 'my-video-{id}');
			video.setAttribute('class', 'video-js vjs-default-skin');
			video.setAttribute('width', '770');
			video.setAttribute('data-height', '500');
			video.setAttribute('controls', ' ');
			video.setAttribute('preload', 'auto');
			video.setAttribute('data-setup', '{{}}');
			let source = document.createElement('source');
			source.setAttribute('type', 'video/mp4');
			source.setAttribute('src', '{path}');
			video.appendChild(source);
			container.appendChild(video);
			let player = videojs(video);
		}}
	}});
	$("#modal3c-{id}").on("hidden.bs.modal",function () {{
		let container = videojs("my-video-{id}");
		container.pause();
	}});
</script>
</div>
</div>
</div>
</div>
"""
#
def replace_text_by_dictionary( text, dict ):
	for key in dict.keys():
		if key in text:
			text = text.replace(key,dict[key])
	return text
#
def remove_curly_bracket( text ):
	return replace_text_by_dictionary(text,{
		'{' : '',
		'}' : '',
	})
#
def fix_jornal( title ):
	return remove_curly_bracket(replace_text_by_dictionary(title,{
		'ACM Trans. Graph.' : 'ACM Transactions on Graphics (TOG)',
		'J. Comput. Phys.' : 'Journal of Computational Physics',
		'Comput. Graph. Forum' : 'Computer Graphics Forum',
	}))
#
def remove_special_chars( text ):
	return replace_text_by_dictionary(text,{
		'{' : '',
		'}' : '',
		'\\' : '',
		'/' : '',
		'.' : '',
		'"' : '',
		'\'' : '',
		'&' : '',
	})
#
def mkpath(dir,file=''):
	return root_dir+'/'+dir+'/'+file
#
# すべての論文ディレクトリを走査
database = {}
for dir in os.listdir(root_dir):
	if os.path.isdir(mkpath(dir)) and not dir in ['__pycache__',resource_dir]:
		#
		print("Processing {}...".format(dir))
		#
		# ファイルリスト
		bib = ''
		year = 0
		title = 'Unknown'
		pdf = 'main.pdf'
		#
		for file in os.listdir(mkpath(dir)):
			for key in video_types:
				if key.upper() in file:
					file = file.replace(key.upper(),key)
			file = unidecode.unidecode(file)
		#
		if not os.path.exists(mkpath(dir,pdf)):
			for file in os.listdir(mkpath(dir)):
				if file.endswith('.pdf'):
					pdf = file
					break
		#
		pdf_reader = PdfFileReader(open(mkpath(dir,pdf),"rb"))
		info = pdf_reader.getDocumentInfo()
		#
		# 動画 ファイルが mp4 でないか、あるいは h264 コーデックでエンコードされていなければ、変換する
		if convert_video:
			for file in os.listdir(mkpath(dir)):
				convert_flag = False
				for key in video_types:
					if file.endswith(key):
						cmd = 'ffprobe -v quiet -show_streams -i {}'.format(mkpath(dir,quote(file)))
						result = subprocess.check_output(cmd.split())
						if '[STREAM]' in str(result) and not 'codec_name=unknown' in str(result):
							if key == '.mp4':
								if 'h264' in str(result):
									print( '{}/{}/{} has codec h264'.format(root_dir,dir,file))
								else:
									print( '{}/{}/{} does not have codec h264'.format(root_dir,dir,file))
									convert_flag = True
							else:
								print( '{}/{}/{} is not mp4'.format(root_dir,dir,file))
								convert_flag = True
						else:
							print( '{}/{}/{} does not have any video stream'.format(root_dir,dir,file))
						break
				if convert_flag:
					if not os.path.exists(mkpath(dir,'converted')):
						os.mkdir(mkpath(dir,'converted'))
					dest_file = '{}/{}/converted/{}.mp4'.format(root_dir,dir,file)
					if not os.path.exists(dest_file):
						os.system('ffmpeg -i {}/{}/{} -pix_fmt yuv420p -b:v 12000k -vcodec libx264 -acodec aac {}'.format(root_dir,dir,file,dest_file))
		#
		# BibTex を読み込む
		for file in os.listdir(mkpath(dir)):
			if file.endswith('.bib'):
				bib = file
				bib_data = parse_file(mkpath(dir,bib))
				fields = bib_data.entries[list(bib_data.entries)[0]].fields
				if 'year' in fields:
					year = int(fields['year'])
				if 'title' in fields:
					title = remove_curly_bracket(fields['title'])
				else:
					title = info.title
		#
		if os.path.exists(mkpath(dir,pdf)):
			#
			# PDF サムネイルを生成する
			if not os.path.exists(mkpath(dir,'thumbnails')):
				print( "Generating thumbnails for {}...".format(dir))
				os.mkdir(mkpath(dir,'thumbnails'))
				os.system('pdftoppm -jpeg -scale-to 680 -f 1 -l {1} {0}/{2} {0}/thumbnails/thumbnail'.format(quote(mkpath(dir)),thumbnail_page_count,quote(pdf)))
				for i in range(thumbnail_page_count):
					good_path = mkpath(dir)+'/thumbnails/thumbnail-{}.jpg'.format(i+1)
					for j in range(4):
						zeros = ''
						for k in range(j+1):
							zeros += '0'
						path = mkpath(dir)+'/thumbnails/thumbnail-{}{}.jpg'.format(zeros,i+1)
						if os.path.exists(path):
							os.rename(path,good_path)
			#
			# PDF から画像を抽出する
			if not os.path.exists(mkpath(dir,'images')) and pdf_reader.getNumPages() <= image_page_limit:
				print( "Extracting images for {}...".format(dir))
				os.mkdir(mkpath(dir,'images'))
				os.system("pdfimages -j {0}/{1} {0}/images/images".format(quote(mkpath(dir)),quote(pdf)))
				os.system("mogrify -format jpg -path {0}/images {0}/images/*".format(quote(mkpath(dir))))
				os.system("find {0}/images -type f ! -name '*.jpg' -delete".format(quote(mkpath(dir))))
				#
				# 解像度があまりにも小さかったり、ファイルサイズが小さいものは削除する
				remove_list = []
				for img in os.listdir(mkpath(dir,'images')):
					img_path = mkpath(dir)+'/images/'+img
					width,height = Image.open(img_path).size;
					if width < image_dimension_limit or height < image_dimension_limit:
						remove_list.append(img_path)
					elif os.path.getsize(img_path) < image_filesize_limit:
						remove_list.append(img_path)
				for img_path in remove_list:
					os.remove(img_path)
			#
			# HTML ファイルを作成する
			if os.path.exists(mkpath(dir,'images')) and len(os.listdir(mkpath(dir,'images'))):
				insert_html = ''
				for img in os.listdir(mkpath(dir,'images')):
					insert_html += '<div class="row">\n'
					insert_html += '<div>\n'
					insert_html += '<a href=\"{0}"><img src="{0}" style="max-width: 100%;"/></a>\n'.format(img)
					insert_html += '</div>\n'
					insert_html += '</div>\n'
				context = {
					'title': title,
					'insert_html' : insert_html,
					'resource_dir' : resource_dir,
				}
				with open('{}/image-template.html'.format(resource_dir),'r') as template:
					data = template.read()
					with open(mkpath(dir)+'/images/index.html','w') as file:
						file.write(data.format_map(context))

		#
		# データベースに登録する
		e = {'pdf':pdf,'dir':dir,'bib':bib}
		if year in database:
			database[year].append(e)
		else:
			database[year] = [e]
#
if not len(database.keys()):
	sys.exit(0)
#
insert_html = ''
min_year = min(database.keys())
max_year = max(database.keys())
video_id = 0
for year in reversed(range(min_year,max_year+1)):
	if year in database:
		#
		insert_html += '\n<div class="row pl-4" style="background-color: LightGray;">{}</div>\n'.format(year if year > 0 else 'Unknown')
		#
		for paper in database[year]:
			#
			pdf = paper['pdf']
			dir = paper['dir']
			bib = paper['bib']
			#
			entry = '\n<!-------------- starting {} -------------->\n'.format(dir)
			entry += '<div class="row">\n'
			entry += '<div class="w-20 p-2">\n'
			#
			entry += "<a href=\"{}\" target=\"_blank\">\n".format(dir+'/'+pdf)
			for i in range(thumbnail_page_count):
				thumbnail = mkpath(dir)+'/thumbnails/thumbnail-{}.jpg'.format(i+1)
				thumbnail_rel = dir+'/thumbnails/thumbnail-{}.jpg'.format(i+1)
				if os.path.exists(thumbnail):
					entry += "<img src=\"{}\" width=\"125\" height=\"170\" class=\"border border\"/>\n".format(thumbnail_rel)
				else:
					dummy_path = mkpath(dir)+'/thumbnails/dummy.png'
					dummy_path_rel = dir+'/thumbnails/dummy.png'
					if not os.path.exists(dummy_path):
						dummy = Image.new("RGB", (16,16), (255, 255, 255))
						dummy.save(dummy_path,"PNG")
					entry += "<img src=\"{}\" width=\"125\" height=\"170\" class=\"border border\"/>\n".format(dummy_path_rel)
			entry += "</a>\n"
			#
			entry += '</div>\n'
			#
			bib_key = ''
			pdf_reader = PdfFileReader(open(mkpath(dir,pdf),"rb"))
			info = pdf_reader.getDocumentInfo()
			table = {}
			if bib:
				#
				bib_data = parse_file(mkpath(dir,bib))
				bib_key = list(bib_data.entries)[0]
				bib_entry = bib_data.entries[bib_key]
				fields = bib_entry.fields
				persons = bib_entry.persons
				#
				if 'author' in persons:
					authors_str = ''
					for i,person in enumerate(persons['author']):
						if len(person.first_names):
							for j,name in enumerate(person.first_names):
								if j == 0:
									authors_str += ' '
								authors_str += name
						if len(person.middle_names):
							for name in person.middle_names:
								authors_str += ' '+remove_special_chars(name)
						if len(person.last_names):
							for name in person.last_names:
								authors_str += ' '+remove_special_chars(name)
						if i < len(persons['author'])-1:
							authors_str += ' and ' if i == len(persons['author'])-2 else ', '
					if not authors_str:
						print( 'WARNING: {} is missing author info.'.format(dir))
					table['author'] = remove_special_chars(authors_str)
				#
				table['bibkey'] = bib_key
				#
				if 'title' in fields:
					table['title'] = remove_curly_bracket(fields['title'])
				if 'journal' in fields:
					table['journal'] = fix_jornal(fields['journal'])
				elif 'booktitle' in fields:
					table['journal'] = fix_jornal(fields['booktitle'])
			else:
				print( 'WARNING: BibTex was not found for {}.'.format(dir))
			#
			if not 'author' in table:
				table['author'] = remove_special_chars(info.author)
			if not 'title' in table:
				table['title'] = info.title
			#
			entry += '<div class="col p-2 pl-3">\n'
			#
			if 'title' in table:
				entry += "<div id=\"{0}\"><h5>{1}</h5></div>\n".format(bib_key,table['title'])
			if 'journal' in table:
				entry += "<div>{} ({})</div>\n".format(table['journal'],year)
			if 'author' in table:
				entry += "<div>{}</div>\n".format(table['author'])
			#
			entry += '<div class="pt-3">\n'
			for file in os.listdir(mkpath(dir)):
				if file.startswith('.'):
					continue
				if not file in ['thumbnails',pdf,'images','converted','analysis'] and not file.endswith('.bib') and not os.path.splitext(file)[1] in video_types:
					entry += '<a href="{}" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">{}</a>\n'.format(dir+'/'+file,file)
				if os.path.splitext(file)[1] in video_types:
					video_id += 1
					if os.path.exists(mkpath(dir)+'/converted/{}.mp4'.format(file)):
						video_path = dir+'/converted/'+file+'.mp4'
					else:
						video_path = dir+'/'+file
					#
					if True:
						entry += video_template.format_map({
							'text' : file,
							'id' : str(video_id),
							'path' : video_path,
							'thumbnail' : 'test.jpg',
						})
					else:
						entry += '<a href="{}" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">{}</a>\n'.format(video_path,file)
			#
			if bib_key:
				entry += '<a href=\"#{0}\" style="padding-right: 0.75rem; white-space: pre;">[{0}]</a>\n'.format(bib_key)
			#
			entry += '<a href=\"{0}\" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">({1})</a>\n'.format(dir,dir)
			#
			image_path = mkpath(dir)+'/images/index.html'
			if os.path.exists(image_path):
				entry += '<a href=\"{0}\" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">[Images]</a>\n'.format(dir+'/images/index.html')

			entry += '</div>\n'
			entry += '</div>\n'
			entry += '</div>\n'
			#
			entry += '<!-------------- ending {} -------------->\n'.format(dir)
			insert_html += entry
#
# HTML ファイルを生成する
context = {
	'page_title' : page_title,
	'insert_html': insert_html,
	'resource_dir' : resource_dir,
}
with open('{}/template.html'.format(resource_dir),'r') as template:
	data = template.read()
	with open(root_dir+'/index.html','w') as file:
		file.write(data.format_map(context))
#
# BibTeX ファイルを生成する
bibtex = ''
for year in reversed(range(min_year,max_year+1)):
	if year in database:
		for paper in database[year]:
			dir = paper['dir']
			bib = paper['bib']
			if bib:
				with open(mkpath(dir,bib),'r') as file:
					bibtex += file.read()
					bibtex += '\n\n'
with open(root_dir+'/bibtex.bib','w') as file:
		file.write(bibtex)
#
# リソースファイルをコピーする
if not os.path.exists(root_dir+'/'+resource_dir):
	os.system('cp -r {} {}'.format(resource_dir,root_dir))