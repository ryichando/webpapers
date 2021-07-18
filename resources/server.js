const vm = require('vm');
const fs = require('fs');
const express = require('express')
const moment = require('moment')
const app = express()
//
// https://stackoverflow.com/questions/14249506/how-can-i-wait-in-node-js-javascript-l-need-to-pause-for-a-period-of-time
const sleep = (waitTimeInMs) => new Promise(resolve => setTimeout(resolve, waitTimeInMs));
//
// installs:
// npm install express moment winston winston-daily-rotate-file
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
app.get('/', async (req, res) => {
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
			const add_year = async function ( year, _res ) {
				if( ! _res.write(JSON.stringify(['add_year',year])+'\n')) {
					while( ! _res.write('\n') ) { await sleep(1); }
				}
			};
			const add_paper = async function ( dir, paper, _res ) {
				if( ! _res.write(JSON.stringify(['add_paper',dir,paper])+'\n')) {
					while( ! _res.write('\n') ) { await sleep(1); }
				}
			};
			const add_snippet = async function ( text, num_found, _res ) {
				if( ! _res.write(JSON.stringify(['add_snippet',text,num_found])+'\n')) {
					while( ! _res.write('\n') ) { await sleep(1); }
				}
			};
			result = await search ( keywords, add_year, add_paper, add_snippet, res );
			if( ! res.write(JSON.stringify(['done',result]))) {
				while( ! res.write('\n') ) { await sleep(1); }
			}
			res.end();
		} else {
			res.send('Array not defined');
		}
	}
});
//
app.listen(server_port, () => {
	print(`server listening at ${server_url}`)
});