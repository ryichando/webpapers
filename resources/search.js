function search ( keywords, add_year, add_paper, add_snippet, param=null, import_js=null ) {
	//
	if( keywords.length == 0 || keywords[0] == "" ) {
		return '';
	}
	//
	const html_escape = function (str) {
		if (!str) return;
		return str.replace(/[<>&"'`]/g, function(match) {
			const escape_chars = {
				'<': '&lt;',
				'>': '&gt;',
				'&': '&amp;',
				'"': '&quot;',
				"'": '&#39;',
				'`': '&#x60;'
			};
		return escape_chars[match];
		});
	};
	//
	let mode = 'word';
	let keywords_dict = {
		'word' : [],
		'title' : [],
		'key' : [],
		'year' : []
	};
	//
	let has_content = false;
	for( let i=0; i<keywords.length; ++i ) {
		const word = keywords[i];
		if( word == 'title:' ) {
			mode = 'title';
		} else if ( word == 'key:' ) {
			mode = 'key';
		} else if ( word == 'year:' ) {
			mode = 'year';
		} else {
			if( mode == 'word') {
				has_content = true;
				for( const w of word.split('-')) {
					if ( w in word_table ) {
						keywords_dict[mode].push(word_table[w]);
					}
				}
			} else {
				if( mode == 'year' ) {
					if( word.indexOf('-') >= 0 ) {
						const pair = word.split('-');
						if( pair.length == 2 ) {
							const year_from = Number(pair[0]);
							const year_to = Number(pair[1]);
							for( let y=year_from; y<=year_to; ++y ) {
								keywords_dict[mode].push(y.toString());
							}
						}
					} else {
						keywords_dict[mode].push(...word.split('-'));
					}
				} else {
					keywords_dict[mode].push(...word.split('-'));
				}
			}
		}
	}
	//
	if( has_content && keywords_dict['word'].length == 0 ) {
		return 'Not found (word not in dictionary)';
	}
	//
	const append_paper = function ( dir, entries, title_highlights=null, show_key=false ) {
		//
		title = papers[dir]['title'];
		for( const w of title_highlights ) {
			const i = title.toLowerCase().indexOf(w.toLowerCase());
			if( i >= 0 ) {
				title = title.substr(0,i)+'<em>'+title.substr(i,w.length)+'</em>'+title.substr(i+w.length,title.length);
			}
		}
		//
		add_paper(dir,papers[dir],title,show_key,param);
		//
		const margin_window = 10;
		for( const elm of entries ) {
			//
			const i = elm['i'];
			const min = elm['min'];
			const max = elm['max'];
			const positions = elm['positions'];
			const num_found = elm['num_found'];
			//
			const get_text = function ( params ) {
				const i = params['idx'];
				const dir = params['dir'];
				let min = params['min'];
				let max = params['max'];
				let words;
				if (typeof window === 'undefined') {
					words = html_escape(Buffer.from(data_words[dir][i],'base64').toString()).split(' ');
				} else {
					words = html_escape(window.atob(data_words[dir][i]).toString()).split(' ');
				}
				for( const pos of positions ) {
					words[pos] = '<em>'+words[pos]+'</em>';
				}
				min = Math.max(0,min-margin_window);
				max = Math.min(words.length,max+margin_window);
				text = words.slice(min,max).join(' ');
				if( max < words.length ) text += '...';
				return text;
			};
			//
			const snippet_id = `snippet-${num_found}`;
			let not_added_snippet = true;
			if( data_words[dir] == undefined ) {
				const path = dir+"/words.js";
				let js = import_js(path);
				if( js ) {
					add_snippet('Loading...',num_found,param,snippet_id);
					js.params = {
						'id' : snippet_id,
						'dir' : dir,
						'idx' : i,
						'min' : min,
						'max' : max,
					};
					js.onload = function() {
						document.getElementById(this.params['id']).innerHTML = get_text(this.params);
					};
					not_added_snippet = false;
				}
			}
			if ( not_added_snippet ) {
				add_snippet(get_text({
					'id' : snippet_id,
					'dir' : dir,
					'idx' : i,
					'min' : min,
					'max' : max,
				}),num_found,param,snippet_id);
			}
		}
	};
	//
	num_found = 0;
	max_year = Math.max.apply(null,Object.keys(papers_yearly));
	min_year = Math.min.apply(null,Object.keys(papers_yearly));
	//
	for( let year=max_year; year>=min_year; --year ) {
		if( year in papers_yearly ) {
			year_found = false;
			dirs = papers_yearly[year];
			for( let dir of dirs ) {
				//
				paper_idx = data_map[dir];
				paper_found = false;
				//
				let paper_pass = [];
				let title_highlights = [];
				let show_key = false;
				if( keywords_dict['title'].length ) {
					//
					let flag = true;
					let title = papers[dir]['title'].toLowerCase();
					for (const word of keywords_dict['title'] ) {
						if( title.indexOf(word.toLowerCase()) < 0 ) {
							flag = false;
							break;
						}
					}
					if( flag ) {
						title_highlights = keywords_dict['title'];
					}
					paper_pass.push(flag);
				}
				//
				if( keywords_dict['key'].length ) {
					let flag = false;
					for (const word of keywords_dict['key'] ) {
						if( dir.indexOf(word) >= 0 ) {
							flag = true;
							show_key = true;
							break;
						}
					}
					paper_pass.push(flag);
				}
				//
				if( keywords_dict['year'].length ) {
					let flag = false;
					for (const y of keywords_dict['year'] ) {
						if( year != Number(y) ) {
							flag = true;
							break;
						}
					}
					paper_pass.push(flag);
				}
				//
				let entries = [];
				if( keywords_dict['word'].length ) {
					for( let i=0; i<data_0[paper_idx].length; ++i ) {
						let min = data_0[paper_idx][i].length;
						let max = 0;
						let positions = [];
						for( const idx of keywords_dict['word'] ) {
							let pos = -1;
							for( let j=0; j<data_0[paper_idx][i].length; ++j ) {
								if( data_0[paper_idx][i][j] == idx ) {
									pos = data_1[paper_idx][i][j];
									break;
								}
							}
							min = Math.min(min,pos)
							max = Math.max(max,pos)
							if( min < 0 ) {
								break;
							}
							if( max - min > word_window_size ) {
								min = -1;
								break;
							}
							positions.push(pos);
						}
						if( min >= 0 ) {
							entries.push({
								'i' : i,
								'min' : min,
								'max' : max,
								'positions' : positions,
								'num_found' : num_found,
							});
							num_found += 1;
							if( num_max_search_hit > 0 && num_found >= num_max_search_hit ) {
								break;
							}
						}
					}
					if( data_words[dir] != undefined ) {
						delete data_words[dir];
					}
					paper_pass.push( entries.length > 0 );
				}
				//
				// https://stackoverflow.com/questions/14832603/check-if-all-values-of-array-are-equal
				const all_true = arr => arr.every( v => v === true )
				if( paper_pass.length && all_true(paper_pass) ) {
					if( ! year_found ) {
						add_year(year,param);
						year_found = true;
					}
					if( ! entries.length ) {
						num_found += 1;
					}
					append_paper(dir,entries,title_highlights,show_key);
				}
				//
				if( num_max_search_hit > 0 && num_found >= num_max_search_hit ) {
					return 'Found '+num_found+' occurrences (exceed max)';
				}
			}
		}
	}
	//
	let search_types = []
	for( const key in keywords_dict ) {
		if( keywords_dict[key].length ) {
			search_types.push(key);
		}
	}
	let status = '';
	if( search_types.length == 1 && search_types[0] == 'word' ) {
		status = '';
	} else if( search_types.length ) {
		status = '('+search_types.join(',')+')';
	}
	if( num_found == 1 ) {
		status += ' Found 1 occurrence';
	} else if( num_found > 1 ) { 
		status += ' Found '+num_found+' occurrences';
	} else {
		status += ' Not found';
	}
	return status;
}