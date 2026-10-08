(function(){var q=document.getElementById('q'),hint=document.getElementById('hint');
var cards=[].slice.call(document.querySelectorAll('.card'));
q.addEventListener('input',function(){var t=q.value.trim().toLowerCase();var n=0;hint.innerHTML='';
cards.forEach(function(c){var e=window.SEARCH_INDEX.find(function(x){return x.acc===c.dataset.acc});var hits=[];
if(t){Object.keys(e.fields).forEach(function(k){if(e.fields[k].toLowerCase().indexOf(t)>-1)hits.push(k)});}
var show=!t||hits.length>0;c.style.display=show?'':'none';c.classList.toggle('hit',!!t&&show);if(show)n++;
var old=c.querySelector('.why');if(old)old.remove();
if(t&&show){var d=document.createElement('p');d.className='why';d.style.fontSize='.85rem';d.textContent='Matches: '+hits.join(', ');c.appendChild(d);}});
if(t)hint.textContent=n+' of '+cards.length+' proteins match.';});})();