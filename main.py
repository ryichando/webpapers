#
# Author: Ryoichi Ando (https://ryichando.graphics)
# License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
#
import os, sys, configparser, subprocess, json, argparse, shutil, pikepdf, pdfdump, base64, nltk, secrets
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
def run_command( cmd ):
	subprocess.call(cmd,shell=True)
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
def mkpath(root,dir,file=''):
	return root+'/'+dir+'/'+file
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
def process_directory( root, dir ):
	#
	print(f'Processing {dir}...')
	#
	# Information list
	bib = None
	doi = None
	year = 0
	title = None
	pdf = 'main.pdf'
	authors = None
	journal = None
	thumbnails = []
	files = []
	videos = []
	#
	# Get main PDF and its info
	if not os.path.exists(mkpath(root,dir,pdf)):
		for file in os.listdir(mkpath(root,dir)):
			if file.endswith('.pdf'):
				pdf = file
				break
	info = pikepdf.open(mkpath(root,dir,pdf))
	#
	for file in os.listdir(mkpath(root,dir)):
		#
		# If the video isn't encoded h264 or the file isn't mp4, convert it
		if convert_video:
			#
			convert_flag = False
			for key in video_types:
				if file.endswith(key):
					cmd = f'ffprobe -v quiet -show_streams -i {mkpath(root,dir,quote(file))}'
					result = subprocess.check_output(cmd.split())
					if '[STREAM]' in str(result) and not 'codec_name=unknown' in str(result):
						if key == '.mp4':
							if 'h264' in str(result):
								print( f'{root}/{dir}/{file} has codec h264' )
							else:
								print( f'{root}/{dir}/{file} does not have codec h264' )
								convert_flag = True
						else:
							print( f'{root}/{dir}/{file} is not mp4' )
							convert_flag = True
					else:
						print( f'{root}/{dir}/{file} does not have any video stream' )
					break
			#
			if convert_flag:
				if not os.path.exists(mkpath(root,dir,'converted')):
					os.mkdir(mkpath(root,dir,'converted'))
				dest_file = f'{root}/{dir}/converted/{file}.mp4'
				if not os.path.exists(dest_file):
					run_command(f'ffmpeg -i {root}/{dir}/{file} -pix_fmt yuv420p -b:v 12000k -vcodec libx264 -acodec aac {dest_file}')
		#
		# Import BibTex
		if file.endswith('.bib'):
			#
			bib = file
			bib_data = parse_file(mkpath(root,dir,bib))
			bib_entry = bib_data.entries[list(bib_data.entries)[0]]
			fields = bib_entry.fields
			#
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
					print( f'WARNING: {dir} is missing author info.')
				authors = remove_special_chars(authors_str)
			#
			if 'journal' in fields:
				journal = fix_jornal(fields['journal'])
			elif 'booktitle' in fields:
				journal = fix_jornal(fields['booktitle'])
		#
		# List files and videos
		if not file.startswith('.'):
			if not file in ['thumbnails',pdf,'images','converted','analysis'] and not file.endswith('.bib') and not os.path.splitext(file)[1] in video_types:
				files.append(file)
			if os.path.splitext(file)[1] in video_types:
				if os.path.exists(mkpath(root,dir)+f'/converted/{file}.mp4'):
					video_path = 'converted/'+file+'.mp4'
				else:
					video_path = file
				videos.append(video_path)
	#
	# Process a PDF
	if os.path.exists(mkpath(root,dir,pdf)):
		#
		# Generate PDF thumbnail
		if not os.path.exists(mkpath(root,dir,'thumbnails')):
			print( "Generating thumbnails for {}...".format(dir))
			os.mkdir(mkpath(root,dir,'thumbnails'))
			run_command('pdftoppm -jpeg -scale-to 680 -f 1 -l {1} {0}/{2} {0}/thumbnails/thumbnail'.format(quote(mkpath(root,dir)),thumbnail_page_count,quote(pdf)))
			for i in range(thumbnail_page_count):
				thumbnail_name = f'/thumbnails/thumbnail-{i+1}.jpg'
				good_path = mkpath(root,dir,thumbnail_name)
				processed = False
				for j in range(4):
					zeros = ''
					for k in range(j+1):
						path = mkpath(root,dir,f'thumbnails/thumbnail-{zeros}{i+1}.jpg')
						zeros += '0'
						if os.path.exists(path):
							os.rename(path,good_path)
							processed = True
							break
					if processed:
						break
				if not processed:
					dummy = Image.new("RGB",(16,16),(255, 255, 255))
					dummy.save(good_path,"PNG")
		for i in range(thumbnail_page_count):
			thumbnail_name = f'thumbnails/thumbnail-{i+1}.jpg'
			good_path = mkpath(root,dir,thumbnail_name)
			thumbnails.append(thumbnail_name)
		#
		# Extract images from PDF
		if not os.path.exists(mkpath(root,dir,'images')) and len(info.pages) <= image_page_limit:
			print( f"Extracting images for {dir}..." )
			os.mkdir(mkpath(root,dir,'images'))
			run_command("pdfimages -j {0}/{1} {0}/images/images".format(quote(mkpath(root,dir)),quote(pdf)))
			run_command("mogrify -format jpg -path {0}/images {0}/images/*".format(quote(mkpath(root,dir))))
			run_command("find {0}/images -type f ! -name '*.jpg' -delete".format(quote(mkpath(root,dir))))
			#
			# Remove if the either the file size is too small or the resolution is too low
			remove_list = []
			for img in os.listdir(mkpath(root,dir,'images')):
				img_path = mkpath(root,dir)+'/images/'+img
				width,height = Image.open(img_path).size;
				if width < image_dimension_limit or height < image_dimension_limit:
					remove_list.append(img_path)
				elif os.path.getsize(img_path) < image_filesize_limit:
					remove_list.append(img_path)
			for img_path in remove_list:
				os.remove(img_path)
		#
		# Generate HTML files for the "images" page
		if os.path.exists(mkpath(root,dir,'images')) and len(os.listdir(mkpath(root,dir,'images'))):
			insert_html = ''
			for img in os.listdir(mkpath(root,dir,'images')):
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
				with open(mkpath(root,dir)+'/images/index.html','w') as file:
					file.write(data.format_map(context))
	#
	image_path = 'images/index.html'
	if not os.path.exists(mkpath(root,dir,image_path)):
		image_path = None
	#
	return {
		'year' : int(year),
		'pdf' : pdf,
		'bib' : bib,
		'doi' : doi,
		'title' : title,
		'authors' : authors,
		'journal' : journal,
		'thumbnails' : thumbnails,
		'files' : files,
		'videos' : videos,
		'image_page' : image_path
	}
#
if __name__ == '__main__':
	#
	# Parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('root', help='Root directory')
	parser.add_argument('--clean', action='store_true')
	args = parser.parse_args()
	root = args.root
	#
	# Load parameters
	config = configparser.ConfigParser()
	config.read('{}/config.ini'.format(root))
	page_title = config['DEFAULT']['page_title']
	thumbnail_page_count = int(config['DEFAULT']['thumbnail_page_count'])
	image_filesize_limit = int(config['DEFAULT']['image_filesize_limit'])
	image_dimension_limit = int(config['DEFAULT']['image_dimension_limit'])
	image_page_limit = int(config['DEFAULT']['image_page_limit'])
	convert_video = config['DEFAULT']['convert_video'] == 'yes'
	enable_search = config['DEFAULT']['enable_search'] == 'yes'
	realtime_search = config['DEFAULT']['realtime_search'] == 'yes'
	server_side_search = config['DEFAULT']['server_side_search'] == 'yes'
	server_port = config['DEFAULT']['server_port']
	server_url = config['DEFAULT']['server_url'].replace('{server_port}',str(server_port))
	num_max_search_hit = int(config['DEFAULT']['num_max_search_hit'])
	resource_dir = 'resources'
	#
	# If the "clean" flag is specified, clean them all
	if args.clean:
		print( 'Cleaning...' )
		for dir in os.listdir(root):
			if dir in ['__pycache__',resource_dir]:
				print( f'Deleting {root}/{dir}...' )
				shutil.rmtree(root+'/'+dir)
			elif dir in ['bibtex.bib','index.html','data.js','papers.js']:
				file = root+'/'+dir
				print( f'Deleting {file}...')
				os.remove(file)
			elif os.path.isdir(root+'/'+dir):
				for subdir in os.listdir(root+'/'+dir):
					if subdir in ['thumbnails','images','converted','analysis']:
						print(f'Deleting {root}/{dir}/{subdir}...')
						shutil.rmtree(root+'/'+dir+'/'+subdir)
		sys.exit(0)
	#
	# List all the file types supported
	video_types = [ '.mp4', '.avi', '.mov', '.flv', '.mpg', '.mpeg', '.m4v' ]
	#
	# Probe all the directories
	database = {}
	database_yearly = {}
	for dir in os.listdir(root):
		if os.path.isdir(mkpath(root,dir)) and not dir in ['__pycache__',resource_dir]:
			e = process_directory(root,dir)
			year = e['year']
			if year in database_yearly.keys():
				database_yearly[year].append(dir)
			else:
				database_yearly[year] = [dir]
			database[dir] = e
	#
	# If no valid directory is found exit the program
	if not len(database):
		sys.exit(0)
	#
	# Generate HTML
	context = {
		'search_hide' : 'hidden' if realtime_search else '',
		'page_title' : page_title,
		'realtime_search' : 'true' if realtime_search else 'false',
		'server_side_search' : 'true' if server_side_search else 'false',
		'include_data_js' : '' if server_side_search else '<script src="data.js"></script>',
		'server_url' : server_url,
	}
	with open('{}/template.html'.format(resource_dir),'r') as template:
		data = template.read()
		with open(root+'/index.html','w') as file:
			file.write(replace_text_by_dictionary(data,context))
	#
	# Build paper references
	data_js = 'data = {};\n'
	#
	# Add search index
	if enable_search:
		#
		word_index = 0
		word_dictionary = load_dictionary('resources/words')
		registered_stem = {}
		registered_words = {}
		stemmer = nltk.PorterStemmer()
		#
		for dir,paper in database.items():
			#
			year = paper['year']
			pdf = paper['pdf']
			print( 'Analyzing {}...'.format(dir))
			lines = pdfdump.dump(mkpath(root,dir,pdf))
			indices = []
			#
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
			data_js += "data['{}'] = {{ 'year' : {}, 'index' : [{}], 'words' : [{}] }};\n".format(
				dir,
				year,
				','.join(['['+','.join([ f'[{y[0]},{y[1]}]' for y in x ])+']' for x in indices]),
				','.join([ "'"+base64.b64encode(line.encode('ascii')).decode("ascii")+"'" for line in lines ])
			)
		#
		# Write word table
		data_js += 'const word_table = {{\n{}\n}};\n'.format(',\n'.join([ f"'{x}' : {y}" for x,y in registered_words.items() ]))
	#
	# Generate Javascript file
	with open(root+'/data.js','w') as file:
		file.write(data_js)
	#
	papers_js = '''
const papers = {0};
const papers_yearly = {1};
'''.format(json.dumps(database),json.dumps(database_yearly))
	#
	papers_js += f'const token = "{secrets.token_urlsafe(8)}"\n'
	papers_js += f'const server_port = {server_port}\n'
	papers_js += f'const num_max_search_hit = {num_max_search_hit}'
	with open(root+'/papers.js','w') as file:
		file.write(papers_js)
	#
	# Generate BibTeX
	entries = {}
	for dir,paper in database.items():
		bib = paper['bib']
		if bib:
			bib_data = parse_file(mkpath(root,dir,bib))
			entries[dir] = bib_data.entries[list(bib_data.entries)[0]]
	with open(root+'/bibtex.bib','w') as file:
			BibliographyData(entries).to_file(file)
	#
	# Copy resources
	run_command('cp -rf {} {}'.format(resource_dir,root))
	run_command('cp -f {}/server.js {}'.format(resource_dir,root))