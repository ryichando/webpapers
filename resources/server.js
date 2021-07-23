//
let vm = require('vm');
let fs = require('fs');
let express = require('express')
let moment = require('moment')
let serveIndex = require('serve-index')
let app = express()
//
// installs:
// npm install --save-dev express moment winston winston-daily-rotate-file serve-index
//
app.get("/", (req, res) => {
	res.status(301).redirect(req.url+'index.html')
});
app.use('/',express.static('/'),serveIndex(__dirname,{'icons': true}));
app.use(express.static(__dirname));
//
// https://stackoverflow.com/questions/11403953/winston-how-to-rotate-logs
let winston = require('winston');
require('winston-daily-rotate-file');
let transport = new (winston.transports.DailyRotateFile)({
	filename: 'logs/server-%DATE%.log',
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
	const script = new vm.Script(fs.readFileSync(path));
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
import_js('./papers.js');
import_js('./data.js');
import_js('./config.js')
import_js('./resources/search.js');
//
app.get('/query', (req, res) => {
	res.header('Access-Control-Allow-Origin','*');
	const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress 
	if( ! req.query.token ) {
		res.status(500)
		res.send('Token not defined');
		print( `ip: ${ip} token undefined`);
	} else if( req.query.token != token ) {
		res.status(500)
		res.send('Wrong token');
		print( `ip: ${ip} wrong token`);
	} else {
		if( req.query.ping ) {
			res.send('Server is ready');
			print( `ip: ${ip} ping`);
		} else if( req.query.array ) {
			const keywords = req.query.array.split(',');
			print( `ip: ${ip} keywords: ${keywords}`);
			const add_year = function ( year, _res ) {
				_res.write(JSON.stringify(['add_year',year])+'\n');
			};
			const add_paper = function ( dir, paper, title, show_key, _res ) {
				_res.write(JSON.stringify(['add_paper',dir,paper,title,show_key])+'\n');
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
	}
});
//
app.listen(server_port, () => {
	print(`server listening at http://localhost:${server_port}`)
});
