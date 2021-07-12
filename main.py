#
# Author: Ryoichi Ando (https://ryichando.graphics)
# License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
#
import os, sys, configparser, subprocess, unidecode, argparse, shutil, pikepdf, pdfdump, base64, nltk
from PIL import Image
from pybtex.database import parse_file, BibliographyData
from shlex import quote
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
		'(' : '',
		')' : '',
		'[' : '',
		']' : '',
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
def load_dictionary( dirpath ):
	with open(dirpath+'/words.txt') as f:
		dictionary = set(f.read().split())
	with open(dirpath+'/words_alpha.txt') as f:
		dictionary = dictionary.union(set(f.read().split()))
	return dictionary
#
def clean( lines, dictionary ):
	#
	results = []
	for line in lines:
		count = 0
		for word in line.split():
			if word in dictionary:
				count += 1
		if count:
			results.append(line)
	#
	return results
#
if __name__ == '__main__':
	#
	# Parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('root_dir', help='Root directory')
	parser.add_argument('--clean', action='store_true')
	args = parser.parse_args()
	root_dir = args.root_dir
	#
	# Load parameters
	config = configparser.ConfigParser()
	config.read('{}/config.ini'.format(root_dir))
	page_title = config['DEFAULT']['page_title']
	thumbnail_page_count = int(config['DEFAULT']['thumbnail_page_count'])
	image_filesize_limit = int(config['DEFAULT']['image_filesize_limit'])
	image_dimension_limit = int(config['DEFAULT']['image_dimension_limit'])
	image_page_limit = int(config['DEFAULT']['image_page_limit'])
	convert_video = config['DEFAULT']['convert_video'] == 'yes'
	enable_search = config['DEFAULT']['enable_search'] == 'yes'
	realtime_search = config['DEFAULT']['realtime_search'] == 'yes'
	resource_dir = 'resources'
	#
	# If the "clean" flag is specified, clean them all
	if args.clean:
		print( 'Cleaning...' )
		for dir in os.listdir(root_dir):
			if dir in ['__pycache__',resource_dir]:
				print( 'Deleting {}/{}...'.format(root_dir,dir))
				shutil.rmtree(root_dir+'/'+dir)
			elif dir in ['bibtex.bib','index.html','data.js']:
				file = root_dir+'/'+dir
				print( 'Deleting {}...'.format(file))
				os.remove(file)
			elif os.path.isdir(root_dir+'/'+dir):
				for subdir in os.listdir(root_dir+'/'+dir):
					if subdir in ['thumbnails','images','converted','analysis']:
						print( 'Deleting {}/{}/{}...'.format(root_dir,dir,subdir))
						shutil.rmtree(root_dir+'/'+dir+'/'+subdir)
		sys.exit(0)
	#
	# List all the file types supported
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
	# Probe all the directories
	database = {}
	for dir in os.listdir(root_dir):
		if os.path.isdir(mkpath(dir)) and not dir in ['__pycache__',resource_dir]:
			#
			print("Processing {}...".format(dir))
			#
			# File list
			bib = ''
			doi = ''
			year = 0
			title = 'Unknown'
			pdf = 'main.pdf'
			authors = 'Unknown'
			journal = 'Unknown'
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
			info = pikepdf.open(mkpath(dir,pdf))
			#
			# If the video isn't encoded h264 or the file isn't mp4, convert it
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
			# Import BibTex
			for file in os.listdir(mkpath(dir)):
				if file.endswith('.bib'):
					bib = file
					bib_data = parse_file(mkpath(dir,bib))
					bib_entry = bib_data.entries[list(bib_data.entries)[0]]
					fields = bib_entry.fields
					if 'doi' in fields:
						doi = fields['doi']
					else:
						print( 'WARNING: doi not found ')
					if 'year' in fields:
						year = int(fields['year'])
					else:
						print( 'WARNING: year not found ')
					if 'title' in fields:
						title = remove_curly_bracket(fields['title'])
					else:
						meta_data = info.open_metadata()
						if 'dc:title' in meta_data:
							title = info.open_metadata()['dc:title']
						else:
							print( 'WARNING: title not found ')
					#
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
						authors = remove_special_chars(authors_str)
					#
					if 'journal' in fields:
						journal = fix_jornal(fields['journal'])
					elif 'booktitle' in fields:
						journal = fix_jornal(fields['booktitle'])
			#
			# Process a PDF
			if os.path.exists(mkpath(dir,pdf)):
				#
				# Generate PDF thumbnail
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
				# Extract images from PDF
				if not os.path.exists(mkpath(dir,'images')) and len(info.pages) <= image_page_limit:
					print( "Extracting images for {}...".format(dir))
					os.mkdir(mkpath(dir,'images'))
					os.system("pdfimages -j {0}/{1} {0}/images/images".format(quote(mkpath(dir)),quote(pdf)))
					os.system("mogrify -format jpg -path {0}/images {0}/images/*".format(quote(mkpath(dir))))
					os.system("find {0}/images -type f ! -name '*.jpg' -delete".format(quote(mkpath(dir))))
					#
					# Remove if the either the file size is too small or the resolution is too low
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
				# Generate HTML files for the "images" page
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
			# Register to the database
			e = {
				'year' : year,
				'pdf' : pdf,
				'dir' : dir,
				'bib' : bib,
				'doi' : doi,
				'title' : title,
				'author' : authors,
				'journal' : journal,
			}
			if year in database:
				database[year].append(e)
			else:
				database[year] = [e]
	#
	if not len(database.keys()):
		sys.exit(0)
	#
	insert_html = ''
	insert_js = 'data = {};\n'
	min_year = min(database.keys())
	max_year = max(database.keys())
	video_id = 0
	word_index = 0
	word_dictionary = load_dictionary('resources/words')
	registered_stem = {}
	registered_words = {}
	stemmer = nltk.PorterStemmer()
	#
	for year in reversed(range(min_year,max_year+1)):
		if year in database:
			#
			insert_html += '\n<div class="row pl-4" style="background-color: LightGray;" id="{}">{}</div>\n'.format(year,year)
			#
			for paper in database[year]:
				#
				pdf = paper['pdf']
				dir = paper['dir']
				#
				entry = '\n<!-------------- starting {} -------------->\n'.format(dir)
				entry += '<div class="row" id="{}">\n'.format(dir)
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
				entry += '</div>\n'
				#
				entry += '<div class="col p-2 pl-3">\n'
				#
				if 'title' in paper:
					entry += "<div id=\"{0}-title\"><h5>{1}</h5></div>\n".format(dir,paper['title'])
				if 'journal' in paper:
					entry += "<div>{} ({})</div>\n".format(paper['journal'],year)
				if 'author' in paper:
					entry += "<div>{}</div>\n".format(paper['author'])
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
						entry += video_template.format_map({
							'text' : file,
							'id' : str(video_id),
							'path' : video_path,
							'thumbnail' : 'test.jpg',
						})
				#
				entry += '<a href=\"{0}\" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">[Files]</a>\n'.format(dir)
				#
				image_path = mkpath(dir)+'/images/index.html'
				if os.path.exists(image_path):
					entry += '<a href=\"{0}\" target=\"_blank\" style="padding-right: 0.75rem; white-space: pre;">[Images]</a>\n'.format(dir+'/images/index.html')
				#
				entry += '</div>\n'
				entry += '</div>\n'
				entry += '</div>\n'
				#
				lines = pdfdump.dump(mkpath(dir,pdf))
				indices = []
				#
				# Build table data
				if enable_search:
					print( 'Analyzing {}...'.format(dir))
					for line in lines:
						line_indices = []
						head_pos = 0
						for _word in line.split(' '):
							for word in remove_special_chars(_word).split('-'):
								normalized_word = None
								if word.lower() in word_dictionary:
									normalized_word = stemmer.stem(word.lower())
									key = word.lower()
								elif word.isupper() and word.isalpha():
									normalized_word = stemmer.stem(word)
									key = word.lower()
								stem_idx = 0
								if normalized_word:
									if normalized_word in registered_stem.keys():
										stem_idx = registered_stem[normalized_word]
									else:
										word_index += 1
										stem_idx = word_index
										registered_stem[normalized_word] = word_index
									if not key in registered_words.keys():
										registered_words[key] = stem_idx
								line_indices.append((stem_idx,head_pos))
							head_pos += 1
						indices.append(line_indices)
					#
					insert_js += "data['{}'] = {{ 'year' : {}, 'index' : [{}], 'words' : [{}] }};\n".format(
						dir,
						year,
						','.join(['['+','.join([ f'[{y[0]},{y[1]}]' for y in x ])+']' for x in indices]),
						','.join([ "'"+base64.b64encode(line.encode('ascii')).decode("ascii")+"'" for line in lines ])
					)
				#
				entry += '<!-------------- ending {} -------------->\n'.format(dir)
				insert_html += entry

	if enable_search:
		#
		# Write word table
		insert_js += 'let word_table = {{\n{}\n}};\n'.format(',\n'.join([ f"'{x}' : {y}" for x,y in registered_words.items() ]))
	#
	# Generate Javascript file
	with open(root_dir+'/data.js','w') as file:
		file.write(insert_js)
	#
	# Generate HTML
	context = {
		'search_hide' : '' if enable_search else 'hidden',
		'page_title' : page_title,
		'insert_html': insert_html,
		'resource_dir' : resource_dir,
		'button_hide' : 'hidden' if realtime_search else '',
		'realtime_search' : 'true' if realtime_search else 'false',
	}
	with open('{}/template.html'.format(resource_dir),'r') as template:
		data = template.read()
		with open(root_dir+'/index.html','w') as file:
			file.write(data.format_map(context))
	#
	# Generate BibTeX
	entries = {}
	for year in reversed(range(min_year,max_year+1)):
		if year in database:
			for paper in database[year]:
				dir = paper['dir']
				bib = paper['bib']
				if bib:
					bib_data = parse_file(mkpath(dir,bib))
					entries[dir] = bib_data.entries[list(bib_data.entries)[0]]
	#
	with open(root_dir+'/bibtex.bib','w') as file:
			BibliographyData(entries).to_file(file)
	#
	# Copy resources
	if not os.path.exists(root_dir+'/'+resource_dir):
		os.system('cp -r {} {}'.format(resource_dir,root_dir))