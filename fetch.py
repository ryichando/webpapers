#
import os, subprocess, sys, argparse, pikepdf, shutil, latexcodec, glob, time, signal, urllib.request, translitcodec, codecs
from pybtex.database import parse_file, BibliographyData
from pathlib import Path
from main import replace_text_by_dictionary
#
def sigint_handler(signal, frame):
	print('')
	print('Interrupted')
	sys.exit(0)
signal.signal(signal.SIGINT, sigint_handler)
#
def check_valid_pdf(path):
	try:
		pikepdf.open(path).open_metadata()
	except:
		return False
	return True
#
def safe_remove( path ):
	try:
		os.remove(path)
	except:
		pass
#
def remove_curly_bracket( text ):
	return replace_text_by_dictionary(text,{
		'{' : '',
		'}' : '',
	})
#
def normalize( text ):
	return codecs.encode(text,'translit/short')
#
def download( root, entry, watch_dir ):
	#
	fields = entry.fields
	persons = entry.persons
	authors = persons['author']
	lastname = remove_curly_bracket(authors[0].last_names[0].lower().encode("ascii","ignore").decode('latex'))
	lastname = normalize(lastname)

	dirname = lastname+str(fields['year'])
	counter = 0
	while True:
		base = os.path.join(root,dirname)
		if counter == 0:
			dirpath = base
		else:
			dirpath = f'{base}-{counter}'
		counter += 1
		bib_files = glob.glob(f'{dirpath}/*.bib')
		pdf_files = glob.glob(f'{dirpath}/*.pdf')
		if bib_files and pdf_files:
			ref_fields = list(parse_file(bib_files[0]).entries.values())[0].fields
			if 'doi' in fields and 'doi' in ref_fields and ref_fields['doi'] == fields['doi']:
				print( f'Found duplicate DOI "{os.path.basename(dirpath)}"' )
				return
			if 'title' in fields and 'title' in ref_fields and ref_fields['title'].lower() == fields['title'].lower():
				print( f'Found duplicate title "{os.path.basename(dirpath)}"' )
				return
			else:
				print( 'Duplicate directory. Increasing counter..' )
				continue
		else:
			save_file_list = os.listdir(watch_dir)
			os.system('open http://www.google.com/search?query={}'.format('+'.join(fields['title'].split())))
			tmp_path = None
			while True:
				for file in os.listdir(watch_dir):
					if file.endswith('.pdf') and file not in save_file_list:
						tmp_path = os.path.join(watch_dir,file)
						break
				if tmp_path:
					break
				time.sleep(1)
			#
			print( f'Saving to {dirpath}...' )
			os.makedirs(dirpath,exist_ok=True)
			new_path = os.path.join(dirpath,'main.pdf')
			cmd = f'gs -o {new_path} -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress -dNOPAUSE -dBATCH {tmp_path}'
			copy_original = False
			try:
				print(cmd)
				subprocess.check_output(cmd,stderr=subprocess.STDOUT,timeout=30,shell=True)
			except Exception as e:
				 print(e)
				 copy_original = True
			#
			if check_valid_pdf(new_path):
				tmp_size = Path(tmp_path).stat().st_size
				new_size = Path(new_path).stat().st_size
				if new_size < tmp_size:
					safe_remove(tmp_path)
				else:
					copy_original = True
			else:
				copy_original = True
			#
			if copy_original:
				safe_remove(new_path)
				shutil.move(tmp_path,new_path)
			#
			# Create bibtex file in it
			new_bibtex = BibliographyData({
				os.path.basename(dirpath) : entry
			})
			new_bibtex.to_file(os.path.join(dirpath,'main.bib'))
			break
#
if __name__ == '__main__':
	#
	parser = argparse.ArgumentParser()
	parser.add_argument('--bib_path', required=True, help='bibtex file path')
	parser.add_argument('--root', required=True, help='root output path')
	parser.add_argument('--watch_dir', required=True, help='downloads watch directory')
	args = parser.parse_args()
	#
	# Load bibtex
	if args.bib_path.startswith('http://') or args.bib_path.startswith('https://'):
		bibtex = urllib.request.urlopen(args.bib_path).read().decode('ascii','ignore')
	else:
		bibtex = parse_file(args.bib_path)
	#
	# For each paper
	NUM_PAPERS = len(list(bibtex.entries.keys()))
	print( f'==== {NUM_PAPERS} papers ====')
	print( f'Download PDFs to "{args.watch_dir}"' )
	#
	for i,key in enumerate(bibtex.entries):
		#
		print('')
		print( f'{NUM_PAPERS-i} papers remaining...' )
		fields = bibtex.entries[key].fields
		print( f'title: "{fields["title"]}"' )
		#
		# Create directory path and download paper
		if 'volume' in fields and 'number' in fields:
			root = os.path.join(args.root,'volume',fields['volume'],fields['number'])
		elif 'year' in fields:
			root = os.path.join(args.root,'year',fields['year'])
		download(root,bibtex.entries[key],args.watch_dir)
	#
	print( 'Done!' )