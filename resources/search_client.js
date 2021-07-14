function search ( keywords, papers_yearly, data, word_table, add_year, add_paper, add_snippet ) {
	//
	let search_from = 'contents';
	for (const word of keywords ) {
		if( word == 'title:' ) {
			search_from = 'title';
			keywords.splice(keywords.indexOf('title:'),1);
			break;
		}
	}
	if( keywords.length == 0 || keywords[0] == "" ) {
		return -1;
	}
	//
	let indices = [];
	if( search_from == 'contents' ) {
		for (const word of keywords ) {
			if ( word in word_table ) {
				indices.push(word_table[word])
			} else {
				return 0;
			}
		}
	}
	//
	num_found = 0;
	max_year = Math.max.apply(null,Object.keys(papers_yearly));
	min_year = Math.min.apply(null,Object.keys(papers_yearly));
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
						let window_size = 10;
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
							if( min < 0 ) break;
							highlights.push(pos);
						}
						if( min >= 0 ) {
							let words = html_escape(atob(value.words[i])).split(' ');
							for( const pos of highlights ) {
								words[pos] = '<em>'+words[pos]+'</em>';
							}
							min = Math.max(0,min-window_size);
							max = Math.min(words.length,max+window_size);
							text = words.slice(min,max).join(' ');
							if( max < words.length ) text += '...';
							//
							if( ! year_found ) {
								add_year(year);
								year_found = true;
							}
							//
							if( ! paper_found ) {
								add_paper(dir);
								paper_found = true;
							}
							num_found += 1;
							add_snippet(text);
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
						add_paper(dir);
						num_found += 1;
					}
				}
			}
		}
	}
	return num_found;
}