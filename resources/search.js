async function search ( keywords, add_year, add_paper, add_snippet ) {
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
	let search_from = 'contents';
	let show_all = false;
	if( keywords.length ) {
		const word = keywords[0];
		if( word == 'title:' ) {
			search_from = 'title';
			keywords.splice(keywords.indexOf('title:'),1);
		} else if( word == 'all:' ) {
			show_all = true;
		}
	}
	if( keywords.length == 0 || keywords[0] == "" ) {
		return '';
	}
	//
	num_found = 0;
	max_year = Math.max.apply(null,Object.keys(papers_yearly));
	min_year = Math.min.apply(null,Object.keys(papers_yearly));
	//
	if( show_all ) {
		for( let year=max_year; year>=min_year; --year ) {
			if( year in papers_yearly ) {
				add_year(year);
				for( let dir of papers_yearly[year] ) {
					add_paper(dir,papers[dir]);
				}
			}
		}
		return 'All the papers';
	}
	//
	let indices = [];
	if( search_from == 'contents' ) {
		for (const word of keywords ) {
			if ( word in word_table ) {
				indices.push(word_table[word])
			} else {
				return 'Not found (word not in dictionary)';
			}
		}
	}
	//
	for( let year=max_year; year>=min_year; --year ) {
		if( year in papers_yearly ) {
			year_found = false;
			dirs = papers_yearly[year];
			for( let dir of dirs ) {
				value = data[dir];
				paper_found = false;
				if( search_from == 'contents' ) {
					for( let i=0; i<value.index.length; ++i ) {
						let min = value.index[i].length;
						let max = 0;
						const margin_window = 10;
						let highlights = [];
						for( const idx of indices ) {
							let pos = -1;
							for( let j=0; j<value.index[i].length; ++j ) {
								if( value.index[i][j][0] == idx ) {
									pos = value.index[i][j][1];
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
							highlights.push(pos);
						}
						if( min >= 0 ) {
							let words;
							if (typeof window === 'undefined') {
								words = html_escape(Buffer.from(value.words[i],'base64').toString()).split(' ');
							} else {
								words = html_escape(window.atob(value.words[i]).toString()).split(' ');
							}
							for( const pos of highlights ) {
								words[pos] = '<em>'+words[pos]+'</em>';
							}
							min = Math.max(0,min-margin_window);
							max = Math.min(words.length,max+margin_window);
							text = words.slice(min,max).join(' ');
							if( max < words.length ) text += '...';
							//
							if( ! year_found ) {
								await add_year(year);
								year_found = true;
							}
							//
							if( ! paper_found ) {
								await add_paper(dir,papers[dir]);
								paper_found = true;
							}
							num_found += 1;
							await add_snippet(text,num_found);
							if( num_max_search_hit > 0 && num_found >= num_max_search_hit ) {
								return 'Found '+num_found+' occurrences (exceed max)';
							}
						}
					}
				} else if ( search_from == 'title' ) {
					let found_all = true;
					let title = papers[dir]['title'].toLowerCase();
					for (const word of keywords ) {
						if( title.indexOf(word) < 0 ) {
							found_all = false;
							break;
						}
					}
					if( found_all ) {
						if( ! year_found ) {
							add_year(year);
							year_found = true;
						}
						num_found += 1;
						add_paper(dir,papers[dir]);
						if( num_max_search_hit > 0 && num_found >= num_max_search_hit ) {
							return '(title) Found '+num_found+' occurrences (exceed max)';
						}
					}
				}
			}
		}
	}
	//
	let status = '';
	if( search_from == 'title' ) {
		status = '(title) ';
	}
	if( num_found == 1 ) {
		status += 'Found 1 occurrence';
	} else if( num_found > 1 ) { 
		status += 'Found '+num_found+' occurrences';
	} else {
		status += 'Not found';
	}
	return status;
}