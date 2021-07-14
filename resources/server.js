const vm = require('vm');
const fs = require('fs');
const express = require('express')
const app = express()
//
// https://stackoverflow.com/questions/4481058/load-and-execute-external-js-file-in-node-js-with-access-to-local-variables
function import_js( path ) {
	console.log(`Loading ${path}`)
	const script = new vm.Script(fs.readFileSync(path));
	script.runInThisContext();
}
import_js('./papers.js');
import_js('./data.js');
import_js('./resources/search.js');
//
app.get('/', (req, res) => {
	res.header('Access-Control-Allow-Origin','*')
	if( ! req.query.token ) {
		res.status(500)
		res.send('Token not defined');
	} else if( req.query.token != token ) {
		res.status(500)
		res.send('Wrong token');
	} else {
		if( req.query.array ) {
			const keywords = req.query.array.split(',');
			const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress 
			console.log( `ip: ${ip} keywords: ${keywords}`);
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
			result.push(['result',search ( keywords, add_year, add_paper, add_snippet )]);
			res.json(result);
		} else {
			res.send('Array not defined');
		}
	}
})
//
app.listen(server_port, () => {
	console.log(`Example app listening at http://localhost:${server_port}`)
})