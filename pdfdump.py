import re, subprocess, argparse
#
def dump( path ):
	#
	cmd = 'pdftotext -enc ASCII7 -q -nopgbrk {} -'.format(path)
	proc = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
	paragraphs = []
	for line in proc.stdout:
		paragraphs.append(line.decode('ascii'))
	#
	stop = False
	buffer = []
	results = []
	#
	for paragraph in paragraphs:
		for line in paragraph.split('\n'):
			if 'references' in line.lower():
				stop = True
				break
			if line:
				buffer.append(line)
		#
		if buffer and buffer[-1][-1] == '.':
			line = ' '.join(buffer).replace('- ','')
			for sentence in re.sub(r'\. ([A-Z])',r'.\n\1',line).split('\n'):
				results.append(sentence)
			buffer = []
		#
		if stop:
			break
	#
	return results
#
if __name__ == '__main__':
	#
	parser = argparse.ArgumentParser()
	parser.add_argument('path', help='PDF path')
	args = parser.parse_args()
	#
	results = dump(args.path)
	for line in results:
		print( line )
		print( '...' )