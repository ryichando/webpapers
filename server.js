//
let vm = require('vm');
let fs = require('fs');
let express = require('express')
let moment = require('moment')
let serveIndex = require('serve-index')
let app = express()
let path = require('path');
//
const root = process.argv[2];
const port = process.argv[3];
//
// installs:
// npm install --save-dev express moment winston winston-daily-rotate-file serve-index
//
app.get('/'+root+'/', (req, res) => {
	res.sendFile(path.join(__dirname,root,'index.html'));
});
app.get('/'+root+'/config.js', (req, res) => {
	fs.readFile(path.join(__dirname,root,'config.js'), 'ascii', (err, data) => {
		if(err) throw err;
		add_lines = [
			'const server_side_search = true;',
			`const server_port = ${port};`
		];
		res.send(data+'\n'+add_lines.join('\n'));
	});
});
app.use('/'+root+'/',serveIndex(path.join(__dirname,root),{'icons': true}));
app.use('/'+root+'/',express.static(path.join(__dirname,root)));
//
// https://stackoverflow.com/questions/11403953/winston-how-to-rotate-logs
let winston = require('winston');
const { assert } = require('console');
require('winston-daily-rotate-file');
let transport = new (winston.transports.DailyRotateFile)({
	filename: path.join(root,'logs','server-%DATE%.log'),
	datePattern: 'YYYY-MM-DD',
	level: 'info'
});
let logger = new (winston.createLogger)({
	transports: [
	  transport
	]
});
//
// https://stackoverflow.com/questions/4481058/load-and-execute-external-js-file-in-node-js-with-access-to-local-variables
function import_js( path ) {
	console.log(`Loading ${path}`)
	const script = new vm.Script(fs.readFileSync(root+'/'+path));
	script.runInThisContext();
	return null;
}
//
function print( text ) {
	const timestamps = moment().format('MMMM Do YYYY, h:mm:ss a')
	const message = `<${timestamps}> `+text;
	console.log(message);
	logger.info(message);
}
//
import_js('papers.js');
import_js('data.js');
//
function toArrayBuffer(buf) {
	let ab = new ArrayBuffer(buf.length);
	let view = new Uint8Array(ab);
	for (let i = 0; i < buf.length; ++i) view[i] = buf[i];
	return ab;
}
console.log('Loading array.bin')
data_array = new Int32Array(toArrayBuffer(fs.readFileSync(root+'/array.bin')))
import_js('config.js');
import_js('resources/search.js');
//
app.get('/'+root+'/query', (req, res) => {
	const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress 
	if( req.query.ping ) {
		res.send('Server is ready');
		print( `ip: ${ip} ping`);
	} else if( req.query.keywords ) {
		const keywords = req.query.keywords.split(' ');
		print( `ip: ${ip} keywords: ${keywords}`);
		const add_year = function ( year, _res ) {
			_res.write(JSON.stringify(['add_year',year])+'\n');
		};
		const add_paper = function ( dir, paper, highlights, show_key, _res ) {
			_res.write(JSON.stringify(['add_paper',dir,paper,highlights,show_key])+'\n');
		};
		const add_snippet = function ( text, _res, snippet_id ) {
			_res.write(JSON.stringify(['add_snippet',text,null,snippet_id])+'\n');
		};
		result = search ( keywords, add_year, add_paper, add_snippet, res, import_js );
		res.write(JSON.stringify(['done',result]));
		res.end();
	} else {
		res.send('Array not defined');
	}
});
//
app.listen(port, '0.0.0.0', () => {
	print(`server listening at http://localhost:${port}/${root}/`)
});
