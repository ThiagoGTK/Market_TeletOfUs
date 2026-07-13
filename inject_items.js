const fs = require('fs');
const html = fs.readFileSync(__dirname + '/codex.html', 'utf8');
const marker = 'const ITEMS = [';
const start = html.indexOf(marker);
if (start === -1) throw new Error('marker not found');
const arrStart = start + marker.length - 1; // at '['
let depth = 0, i = arrStart, inStr = false, strCh = '', esc = false;
for (; i < html.length; i++) {
  const c = html[i];
  if (inStr) {
    if (esc) esc = false;
    else if (c === '\\') esc = true;
    else if (c === strCh) inStr = false;
    continue;
  }
  if (c === '"' || c === "'" || c === '`') { inStr = true; strCh = c; continue; }
  if (c === '[') depth++;
  else if (c === ']') { depth--; if (depth === 0) { i++; break; } }
}
// i now points right after the closing ']', expect a ';' next
let end = i;
if (html[end] === ';') end++;

const newItems = fs.readFileSync(__dirname + '/items.js.txt', 'utf8').trim();
const newSnippet = newItems.endsWith(';') ? newItems : newItems + ';';

const result = html.slice(0, start) + newSnippet + html.slice(end);
fs.writeFileSync(__dirname + '/codex.html', result);
console.log('replaced', end - start, 'chars with', newSnippet.length, 'chars');
