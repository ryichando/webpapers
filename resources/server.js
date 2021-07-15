const vm = require('vm');
const fs = require('fs');
const express = require('express')
const moment = require('moment')
const app = express()
//
// installs:
// npm install express moment winston winston-daily-rotate-file
//
// https://stackoverflow.com/questions/11403953/winston-how-to-rotate-logs
let winston = require('winston');
require('winston-daily-rotate-file');
let transport = new (winston.transports.DailyRotateFile)({
	filename: './log/log',
	datePattern: 'yyyy-MM-dd',
	prepend: true,
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
import_js('./papers.js');
import_js('./data.js');
import_js('./config.js')
import_js('./resources/search.js');
//
app.get('/', (req, res) => {
	res.header('Access-Control-Allow-Origin','*')
	const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress 
	const timestamps = moment().format('MMMM Do YYYY, h:mm:ss a')
	if( ! req.query.token ) {
		res.status(500)
		res.send('Token not defined');
		logger.info( `<${timestamps}> ip: ${ip} token undefined`);
	} else if( req.query.token != token ) {
		res.status(500)
		res.send('Wrong token');
		logger.info( `<${timestamps}> ip: ${ip} wrong token`);
	} else {
		if( req.query.ping ) {
			res.send('Server is ready');
			logger.info( `<${timestamps}> ip: ${ip} ping`);
		} else if( req.query.array ) {
			const keywords = req.query.array.split(',');
			logger.info( `<${timestamps}> ip: ${ip} keywords: ${keywords}`);
			result = [];
			const add_year = function ( year ) {
				result.push(['add_year',year]);
			};
			const add_paper = function ( dir ) {
				result.push(['add_paper',dir]);
			};
			const add_snippet = function ( text ) {
				result.push(['add_snippet',text]);
			};
			result.push(['done',search ( keywords, add_year, add_paper, add_snippet )]);
			res.json(result);
		} else {
			res.send('Array not defined');
		}
	}
})
//
app.listen(server_port, () => {
	logger.info(`server listening at ${server_url}`)
})