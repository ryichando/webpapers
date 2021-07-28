#
# Author: Ryoichi Ando (https://ryichando.graphics)
# License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/)
#
# Build Library:
# > docker run -u $UID:$GID -v ${PWD}:/root -ti --rm webpapers papers
#
# Server Mode:
# > docker run -u $UID:$GID -v ${PWD}:/root -p 3600:3600 -ti --rm webpapers --server papers
#
import os, sys, configparser, subprocess, json, argparse, latexcodec, time, signal ,logging
import shutil, pikepdf, pdfdump, base64, nltk, secrets, re
from psutil import virtual_memory
from PIL import Image
from pybtex.database import parse_file
from shlex import quote
from tqdm import tqdm
import pprint as pp
#
# Set logging
logfile_name = 'webpapers.log'
logging.basicConfig(
	filename=logfile_name,
	level=logging.INFO,
	format='<%(asctime)s> %(levelname)s: %(message)s',
	datefmt='%d-%b-%y %H:%M:%S %Z',
)
logger = logging.getLogger(__name__)
def _print( text ):
	logger.info(text)
	print(text)
#
def replace_text_by_dictionary( text, dict ):
	if dict:
		for key in dict.keys():
			if key in text:
				text = text.replace(key,dict[key])
		return text
	else:
		return text
#
def remove_curly_bracket( text ):
	return replace_text_by_dictionary(text,{
		'{' : '',
		'}' : '',
	})
#
def fix_jornal( title ):
	return replace_text_by_dictionary(remove_curly_bracket(title),journal_table)
#
def run_command( cmd ):
	logger.info(cmd)
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
		',' : '',
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
def check_valid_pdf(path):
	try:
		pikepdf.open(path).open_metadata()
	except:
		return False
	return True
#
# https://stackoverflow.com/questions/6330071/safe-casting-in-python
def safe_cast(val, to_type, default=None):
	try:
		return to_type(val)
	except (ValueError, TypeError):
		return default
#
def is_paper_directory( dirpath ):
	pdf = None
	bib = None
	for file in os.listdir(dirpath):
		if file.endswith('.pdf'):
			pdf = file
		if file.endswith('.bib'):
			bib = file
	return bib and pdf
#
def process_directory( root, dir ):
	#
	# Information list
	bib = None
	doi = None
	abstract = None
	year = 0
	title = None
	pdf = 'main.pdf'
	volume = None
	number = None
	authors = None
	journal = None
	image_path = None
	pdf_broken = False
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
	#
	if not os.path.exists(mkpath(root,dir,pdf)):
		return None
	#
	if not check_valid_pdf(mkpath(root,dir,pdf)):
		pdf_broken = True
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
							if not 'h264' in str(result):
								convert_flag = True
						else:
							convert_flag = True
					break
			#
			if convert_flag:
				if not os.path.exists(mkpath(root,dir,'converted')):
					os.mkdir(mkpath(root,dir,'converted'))
				dest_file = f'{root}/{dir}/converted/{file}.mp4'
				if not os.path.exists(dest_file):
					logger.info(f'Converting videso for {dir}/{file}...')
					run_command(f'ffmpeg -i {root}/{dir}/{file} -pix_fmt yuv420p -b:v 12000k -vcodec libx264 -acodec aac {dest_file}')
		#
		# Import BibTex
		if file.endswith('.bib'):
			#
			bib = file
			try:
				bib_data = parse_file(mkpath(root,dir,bib))
			except:
				_print( f'Parsing bibtex failed. Check the file: {mkpath(root,dir,bib)}' )
				sys.exit()
			bib_entry = bib_data.entries[list(bib_data.entries)[0]]
			fields = bib_entry.fields
			#
			if 'abstract' in fields:
				abstract = fields['abstract']
			if 'doi' in fields:
				doi = fields['doi']
			if 'year' in fields:
				year = safe_cast(fields['year'],int)
			else:
				logger.info( 'WARNING: year not found ')
			if 'volume' in fields:
				volume = fields['volume']
			if 'number' in fields:
				number = fields['number']
			if 'title' in fields:
				title = remove_curly_bracket(remove_curly_bracket(fields['title'].encode("ascii","ignore").decode('latex')))
				if title.lower() == "editorial":
					return None
				if 'session details:' in title.lower():
					return None
				if 'research' in title.lower() and 'award' in title.lower():
					return None
			else:
				info = pikepdf.open(os.path.join(root,dir,pdf))
				meta_data = info.open_metadata()
				if 'dc:title' in meta_data:
					title = info.open_metadata()['dc:title']
				else:
					logger.info( 'WARNING: title not found ')
			persons = bib_entry.persons
			#
			def normalize_name( name ):
				return remove_special_chars(name.encode("ascii","ignore").decode('latex'))
			#
			if 'author' in persons:
				authors_str = ''
				for i,person in enumerate(persons['author']):
					if len(person.first_names):
						for j,name in enumerate(person.first_names):
							if j == 0:
								authors_str += ' '
							authors_str += normalize_name(name)
					if len(person.middle_names):
						for name in person.middle_names:
							authors_str += ' '+normalize_name(name)
					if len(person.last_names):
						for name in person.last_names:
							authors_str += ' '+normalize_name(name)
					if i < len(persons['author'])-1:
						authors_str += ' and ' if i == len(persons['author'])-2 else ', '
				if not authors_str:
					logger.info( f'WARNING: {dir} is missing author info.')
				authors = authors_str
			#
			if 'journal' in fields:
				journal = fix_jornal(fields['journal'].encode("ascii","ignore").decode('latex'))
			elif 'booktitle' in fields:
				journal = fix_jornal(fields['booktitle'].encode("ascii","ignore").decode('latex'))
		#
		# List files and videos
		if not file.startswith('.'):
			if not file in ignore_files+[pdf] and not file.endswith('.bib') and not os.path.splitext(file)[1] in video_types:
				files.append(file)
			if os.path.splitext(file)[1] in video_types:
				if os.path.exists(mkpath(root,dir)+f'/converted/{file}.mp4'):
					video_path = 'converted/'+file+'.mp4'
				else:
					video_path = file
				videos.append(video_path)
	#
	# Process a PDF
	if not pdf_broken:
		#
		# Generate PDF thumbnail
		create_flag = False
		for i in range(thumbnail_page_count):
			thumbnail_name = f'thumbnails/thumbnail-{i+1}.jpg'
			if not os.path.exists(mkpath(root,dir,thumbnail_name)):
				create_flag = True
				break
			try:
				Image.open(mkpath(root,dir,thumbnail_name)).verify()
			except:
				create_flag = True
				break
		if create_flag:
			logger.info(f'Generating thumbnails for {dir}...')
			os.makedirs(mkpath(root,dir,'thumbnails'),exist_ok=True)
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
		if extract_images:
			if not os.path.exists(mkpath(root,dir,'images')) and len(info.pages) <= image_page_limit:
				os.mkdir(mkpath(root,dir,'images'))
				logger.info(f'Generating images for {dir}...')
				run_command("pdfimages -j {0}/{1} {0}/images/images".format(quote(mkpath(root,dir)),quote(pdf)))
				run_command("mogrify -format jpg -path {0}/images {0}/images/*".format(quote(mkpath(root,dir))))
				run_command("find {0}/images -type f ! -name '*.jpg' -delete".format(quote(mkpath(root,dir))))
				#
				# Remove if the either the file size is too small or the resolution is too low
				remove_list = []
				for img in os.listdir(mkpath(root,dir,'images')):
					img_path = mkpath(root,dir,'images/')+img
					try:
						width,height = Image.open(img_path).size;
						if width < image_dimension_limit or height < image_dimension_limit:
							remove_list.append(img_path)
						elif os.path.getsize(img_path) < image_filesize_limit:
							remove_list.append(img_path)
					except:
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
		'abstract' : abstract,
		'year' : year,
		'volume' : safe_cast(volume,int) if volume else None,
		'number' : safe_cast(number,int) if number else None,
		'pdf' : pdf,
		'bib' : bib,
		'doi' : doi,
		'title' : title,
		'authors' : authors,
		'journal' : journal,
		'thumbnails' : thumbnails,
		'files' : files,
		'videos' : videos,
		'image_page' : image_path,
		'pdf_broken' : pdf_broken,
	}
#
def asciify( str ):
	return str.encode("ascii","ignore").decode()
#
def signal_handler_server(signal, frame):
	print('')
	_print('Stopping..')
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler_server)
#
if __name__ == '__main__':
	#
	logger.info( '--------- Starting up ---------')
	#
	# Global variables
	merge_always = None
	ignore_files = ['thumbnails','images','converted','analysis','info.json','words.js']
	#
	# Parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('root', help='Root directory')
	parser.add_argument('--clean', help='Clean flag')
	parser.add_argument('--server', action='store_true')
	parser.add_argument('--port', type=int, default=3600, help='Server port')
	args = parser.parse_args()
	root = args.root
	#
	if args.server:
		_print( 'Running server mode...' )
		gb_mem = virtual_memory().total / 1024 / 1024 / 1024
		using_mb = int(0.85 * gb_mem * 1024)
		_print( f'{"%.2f" % gb_mem} GB memory detected, setting max to {"%.2f" % (using_mb/1024)} GB...' )
		subprocess.call(f'node server.js {root} {args.port}',shell=True,env={'NODE_OPTIONS':f'--max-old-space-size={using_mb}'})
		sys.exit()
	#
	# Load parameters
	config = configparser.ConfigParser()
	config.read('{}/config.ini'.format(root))
	page_title = config['DEFAULT']['page_title']
	thumbnail_page_count = int(config['DEFAULT']['thumbnail_page_count'])
	extract_images = config['DEFAULT']['extract_images'] == 'yes'
	image_filesize_limit = int(config['DEFAULT']['image_filesize_limit'])
	image_dimension_limit = int(config['DEFAULT']['image_dimension_limit'])
	image_page_limit = int(config['DEFAULT']['image_page_limit'])
	convert_video = config['DEFAULT']['convert_video'] == 'yes'
	check_duplicates = config['DEFAULT']['check_duplicates'] == 'yes'
	journal_table_file = config['DEFAULT']['journal_table'] if config.has_option('DEFAULT','journal_table') else None
	enable_search = config['DEFAULT']['enable_search'] == 'yes'
	realtime_search = config['DEFAULT']['realtime_search'] == 'yes'
	num_max_search_hit = int(config['DEFAULT']['num_max_search_hit'])
	show_all = config['DEFAULT']['show_all'] == 'yes'
	word_window_size = int(config['DEFAULT']['word_window_size'])
	resource_dir = 'resources'
	#
	# Load journabl table
	journal_table = {}
	if journal_table_file:
		with open(os.path.join(root,journal_table_file)) as fp:
			lines = fp.readlines()
			for line in lines:
				row = [name.strip() for name in line.split('==>')]
				journal_table[row[0]] = row[1]
	#
	# If the "clean" flag is specified, clean them all
	if args.clean:
		_print( f'Cleaning...{args.clean}' )
		clean_lists = []
		if args.clean == 'all' or args.clean == 'data':
			clean_lists.extend(['index.html','data.js','papers.js','config.js'])
		if args.clean == 'all' or args.clean == 'thumbnail':
			clean_lists.append('thumbnails')
		if args.clean == 'all' or args.clean == 'image':
			clean_lists.append('images')
		if args.clean == 'all' or args.clean == 'video':
			clean_lists.append('converted')
		#		
		for dir in os.listdir(root):
			if dir in ['__pycache__',resource_dir]:
				_print( f'Deleting {root}/{dir}...' )
				shutil.rmtree(root+'/'+dir)
			elif dir in clean_lists:
				file = root+'/'+dir
				_print( f'Deleting {file}...')
				os.remove(file)
		for current_dir, dirs, files in os.walk(root):
			for dir in dirs:
				if dir in clean_lists:
					_print(f'Deleting {current_dir}/{dir}...')
					shutil.rmtree(current_dir+'/'+dir)
		sys.exit(0)
	#
	# List all the file types supported
	video_types = [ '.mp4', '.avi', '.mov', '.flv', '.mpg', '.mpeg', '.m4v' ]
	#
	# Probe all the directories
	database = {}
	database_yearly = {}
	inconsistent_list = []
	broken_list = {}
	paper_directories = []
	tmp_idx = 0
	for current_dir, dirs, files in os.walk(root):
		for dir in dirs:
			if is_paper_directory(os.path.join(current_dir,dir)):
				paper_directories.append((current_dir,dir))
				print(f'Found {len(paper_directories)} directories.',end='\r')
	#
	print('')
	_print(f'Processing {len(paper_directories)} directories...')
	for (current_dir,dir) in tqdm(paper_directories):
		if not dir in ['__pycache__',resource_dir,'images','converted','thumbnails']:
			path = current_dir+'/'+dir
			dir = '/'.join(path.split('/')[1:])
			e = process_directory(path.split('/')[0],dir)
			if e:
				if e['pdf_broken']:
					broken_list[dir] = e
					continue
				if e['volume'] and e['number']:
					matches = re.findall(r'volume\/(\d.)\/(\d.)',dir)
					if matches:
						volume = int(matches[0][0])
						number = int(matches[0][1])
						if volume == e['volume'] and number == e['number']:
							pass
						else:
							inconsistent_list.append(dir)
							logger.info( 'WARNING: Inconsistent volume and number!' )
				#
				year = e['year']
				matches = re.findall(r'year\/(\d\d\d\d)',dir)
				if matches:
					_year = int(matches[0])
					if not year == _year:
						inconsistent_list.append(dir)
						logger.info( f'WARNING: Inconsistent year! ({_year} != {year})' )
				#
				if year in database_yearly.keys():
					database_yearly[year].append(dir)
				else:
					database_yearly[year] = [dir]
				database[dir] = e | { 'tmp_idx' : tmp_idx }
				tmp_idx += 1
	#
	if broken_list.keys():
		_print( '--------- Papers with broken PDF ----------' )
		for dir,e in broken_list.items():
			_print( f'title: {e["title"]}')
			_print( f'doi: {e["doi"]}')
			_print( f'journal: {e["journal"]}')
			_print( f'volume: {e["volume"]}')
			_print( f'number: {e["number"]}')
			_print( f'year: {e["year"]}')
			_print( f'path: {os.path.join(root,dir)}' )
			_print( '----')
		#
		num_remainings = len(broken_list.keys())
		_print( f'{num_remainings} papers' )
		if input('Fix? [yes/no]: ') == 'yes':
			for dir,e in broken_list.items():
				shutil.rmtree(os.path.join(root,dir,"thumbnails"),ignore_errors=True)
				shutil.rmtree(os.path.join(root,dir,"images"),ignore_errors=True)
				pdf_path = os.path.join(root,dir,e["pdf"])
				_print( f'title: {e["title"]}' )
				_print( f'path: {pdf_path}' )
				url = input('Enter PDF url: ')
				if url:
					headers = {
						"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "+
						"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
					}
					options = f'--user-agent="{headers["User-Agent"]}"'
					subprocess.call(f'wget {options} -O {pdf_path} {url}',shell=True)
				#
				ask_for_delete = False
				if os.path.exists(pdf_path):
					if check_valid_pdf(pdf_path):
						_print( 'Successfully confirmed new PDF' )
					else:
						_print( 'PDF now exists but still broken...' )
						ask_for_delete = True
				else:
					_print('PDF still does not exist.')
					ask_for_delete = True
				#
				if ask_for_delete:
					if input('Delete? [yes/no]: ') == 'yes':
						rm_path = os.path.join(root,dir)
						_print( f'Deleting {rm_path}...' )
						shutil.rmtree(rm_path)
				time.sleep(3)
				print('')
				num_remainings -= 1
				_print( f'--- {num_remainings} papers remaining... ---' )
		sys.exit()
	#
	if inconsistent_list:
		_print( '--------- inconsistent papers ----------' )
		for dir in inconsistent_list:
			_print( f'{dir}: year = {database[dir]["year"]} volume = {database[dir]["volume"]} number = {database[dir]["number"]}' )
		sys.exit()
	#
	# Duplicates
	if check_duplicates:
		#
		_print( 'Checking for paper duplicates...' )
		duplicate_papers = []
		for key_0,entry_0 in tqdm(database.items()):
			for key_1,entry_1 in database.items():
				if entry_0['tmp_idx'] < entry_1['tmp_idx']:
					idential = False
					if entry_0['doi'] and entry_1['doi']:
						idential = entry_0['doi'] == entry_1['doi']
					if entry_0['title'] and entry_1['title']:
						idential = idential or entry_0['title'].lower() == entry_1['title'].lower()
					if idential:
						duplicate_papers.append((key_0,key_1))
		#
		if duplicate_papers:
			delete_dir_key = None
			#
			def merge_files( key_from, key_to ):
				files_to_merge = []
				global merge_always
				if merge_always == False:
					return
				for file in os.listdir(os.path.join(root,key_from)):
					if not file.endswith('.bib') and file not in ignore_files:
						if file != database[key_from]['pdf'] and not os.path.exists(os.path.join(root,key_to,file)):
							files_to_merge.append(file)
				if files_to_merge:
					_print( f'Files not found in dest: {files_to_merge}')
					_print( f'---- List of files in {key_from} ----' )
					pp.pprint(os.listdir(os.path.join(root,key_from)))
					_print( f'---- List of files in {key_to} ----' )
					pp.pprint(os.listdir(os.path.join(root,key_to)))
					do_merge = False
					if merge_always == True:
						do_merge = True
					elif merge_always == False:
						do_merge = False
					else:
						for file in files_to_merge:
							_print( f'"{os.path.join(root,key_from,file)}" -> "{os.path.join(root,key_to,file)}"')
						print('')
						while True:
							answer = input('Move them? [yes/no/yes_always/no_always]: ')
							if answer == 'yes':
								do_merge = True
								break
							elif answer == 'yes_always':
								do_merge = True
								merge_always = True
								break
							elif answer == 'no_always':
								do_merge = False
								merge_always = False
								break
					if do_merge:
						_print( 'Moving...')
						for file in files_to_merge:
							from_path = os.path.join(root,key_from,file)
							to_path = os.path.join(root,key_to,file)
							_print( f'"{from_path}" -> "{to_path}"')
							shutil.move(from_path,to_path)
			#
			num_remainings = len(duplicate_papers)
			_print( f'---------{num_remainings} duplicate(s) found ---------')
			remove_keys = []
			for key_0,key_1 in duplicate_papers:
				if key_0 in remove_keys or key_1 in remove_keys:
					num_remainings -= 1
					_print( f'{num_remainings} duplicates remaining...' )
					continue
				_print( '' )
				_print( f'"{key_0}" <==> "{key_1}"')
				if 'title' in database[key_0] and 'title' in database[key_1]:
					_print( f'{database[key_0]["title"]} <==> {database[key_1]["title"]}' )
				if 'doi' in database[key_0] and 'doi' in database[key_1]:
					_print( f'{database[key_0]["doi"]} <==> {database[key_1]["doi"]}' )
				while True:
					if delete_dir_key:
						if delete_dir_key in key_0:
							merge_files(key_0,key_1)
							_print( f'Removing ({key_0})...' )
							shutil.rmtree(os.path.join(root,key_0))
							remove_keys.append(key_0)
						elif delete_dir_key in key_1:
							merge_files(key_1,key_0)
							_print( f'Removing ({key_1})...' )
							shutil.rmtree(os.path.join(root,key_1))
							remove_keys.append(key_1)
						else:
							_print( 'Skipping...' )
						break
					else:
						print('')
						while True:
							choice = input('Remove? [abord 0] [left 1] [right 2] [neither 3] [both 4] [special 5]: ')
							try:
								choice = int(choice)
							except:
								continue
							if choice >= 0 and choice <= 5:
								break
						if choice == 0:
							_print( 'Abording.' )
							sys.exit()
						elif choice == 1:
							merge_files(key_0,key_1)
							_print( f'Removing left... ({key_0})' )
							shutil.rmtree(os.path.join(root,key_0))
							remove_keys.append(key_0)
							break
						elif choice == 2:
							merge_files(key_1,key_0)
							_print( f'Removing right... ({key_1})' )
							shutil.rmtree(os.path.join(root,key_1))
							remove_keys.append(key_1)
							break
						elif choice == 3:
							_print( 'Skipping...' )
							break
						elif choice == 4:
							_print( f'Removing both... ({key_0},{key_1})' )
							shutil.rmtree(os.path.join(root,key_0))
							shutil.rmtree(os.path.join(root,key_1))
							remove_keys.append(key_0)
							remove_keys.append(key_1)
						elif choice == 5:
							delete_dir_key = input('Enter a name of portion of path that will be always chosen to delete: ')
							if delete_dir_key:
								_print( 'set '+delete_dir_key )
								continue
							else:
								_print( 'Not set. Skipping...' )
								break
				num_remainings -= 1
				_print( '' )
				_print( f'{num_remainings} duplicates remaining...' )
			for key in remove_keys:
				del database[key]
	#
	# If no valid directory is found exit the program
	if not len(database):
		sys.exit(0)
	#
	# Generate HTML
	with open('{}/template.html'.format(resource_dir),'r') as template:
		data = template.read()
		with open(root+'/index.html','w') as file:
			file.write(data)
	#
	# Build paper references
	data_0_js = 'data_0 = [];\n'
	data_1_js = 'data_1 = [];\n'
	data_map = {}
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
		# Extend word dictionary
		_print('Extending word dict from abstracts...')
		abstract_papers = []
		for _,paper in database.items():
			if paper['abstract']:
				abstract_papers.append(paper)
		for paper in tqdm(abstract_papers):
			abstract_lines = paper['abstract'].split('\n')
			for abstract_line in abstract_lines:
				for _word in asciify(abstract_line).split(' '):
					for word in remove_special_chars(_word).split('-'):
						w = word.lower()
						if w not in word_dictionary:
							word_dictionary.add(w)
		#
		data_0_js = 'data_0 = [\n'
		data_1_js = 'data_1 = [\n'
		idx = 0
		_print( 'Analyzing...' )
		for dir,paper in tqdm(database.items()):
			#
			year = paper['year']
			pdf = paper['pdf']
			lines = pdfdump.dump(mkpath(root,dir,pdf))
			#
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
			# Future work
			# base64.b64encode(b''.join([x.to_bytes(4,'little') for x in [10000,20000,30000,400000]])).decode()
			#
			# // https://stackoverflow.com/questions/8609289/convert-a-binary-nodejs-buffer-to-javascript-arraybuffer/12101012
			# function toArrayBuffer(buf) {
			# 	var ab = new ArrayBuffer(buf.length);
			# 	var view = new Uint8Array(ab);
			# 	for (var i = 0; i < buf.length; ++i) {
			# 		view[i] = buf[i];
			# 	}
			# 	return ab;
			# }
			# const str = 'ECcAACBOAAAwdQAAgBoGAA==';
			# const buffer = toArrayBuffer(Buffer.from(str,'base64'));
			# let int32View = new Int32Array(buffer);
			# for (let i = 0; i < int32View.length; i+=1) {
			# 	console.log(int32View[i]);
			# }
			#
			data_0_js += "[{}],\n".format(
				','.join(['['+','.join([ str(y[0]) for y in x ])+']' for x in indices])
			)
			data_1_js += "[{}],\n".format(
				','.join(['['+','.join([ str(y[1]) for y in x ])+']' for x in indices])
			)
			data_map[dir] = idx
			idx += 1
			#
			# Write raw words
			words = ','.join([ "'"+base64.b64encode(line.encode('ascii','ignore')).decode()+"'" for line in lines ])
			additional_words_data = f"data_words['{dir}'] = [{words}];"
			with open(os.path.join(root,dir,'words.js'),'w') as file:
				file.write(additional_words_data)
		#
		# Write word table
		data_0_js += '];\n'
		data_1_js += '];\n'
		#
		data_1_js += 'const data_map = {{ {} }};\n'.format(','.join([ f"'{x}' : {y}" for x,y in data_map.items()]) )
		data_1_js += 'const word_table = {{\n{}\n}};\n'.format(',\n'.join([ f"'{x}' : {y}" for x,y in registered_words.items() ]))
		data_1_js += 'let data_words = {};\n'
	#
	# Generate Javascript file
	with open(root+'/data.js','w') as file:
		file.write(data_0_js)
		file.write(data_1_js)
	#
	papers_js = '''
const papers = {0};
const papers_yearly = {1};
'''.format(json.dumps(database),json.dumps(database_yearly))
	with open(root+'/papers.js','w') as file:
		file.write(papers_js)
	#
	config_js = ''
	config_js += f'const num_max_search_hit = {num_max_search_hit};\n'
	config_js += f'const show_all = {"true" if show_all else "false"};\n'
	config_js += f'const word_window_size = {word_window_size};\n'
	config_js += f'const realtime_search = {"true" if realtime_search else "false"};\n'
	config_js += f'const page_title = "{page_title}";\n'
	config_js += f'const enable_search = {"true" if enable_search else "false"};\n'
	#
	with open(root+'/config.js','w') as file:
		file.write(config_js)
	#
	# Copy resources
	run_command('cp -rf {} {}'.format(resource_dir,root))
	logger.info( '--------- Done ---------')