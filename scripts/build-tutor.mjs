#!/usr/bin/env node
/**
 * build-tutor.mjs — content/tutor.json + templates/tutor.template.html → tutor.html
 *
 * 의존성 0 (Node 내장만). 편집자는 content/tutor.json만 만진다 (Sveltia CMS /admin 폼).
 * 초경량 서식: **굵게** → <b>, `코드` → <code>, *기울임* → <i>. 그 외 HTML은 이스케이프.
 * fail-closed: 미치환 {{...}} 플레이스홀더가 남으면 빌드 실패 (라이브를 깨느니 멈춘다).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const content = JSON.parse(readFileSync(join(root, 'content', 'tutor.json'), 'utf8'));
const template = readFileSync(join(root, 'templates', 'tutor.template.html'), 'utf8');

/** HTML 이스케이프 후 초경량 서식만 태그로 복원 */
function md(s) {
  if (typeof s !== 'string') throw new Error(`문자열이 아닌 값: ${JSON.stringify(s)}`);
  return s
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+(?:\*(?!\*)[^*]*)*)\*\*/g, '<b>$1</b>')
    .replace(/\*([^*\n]+)\*/g, '<i>$1</i>');
}

/** 중첩 객체를 "a.b.c" 플레이스홀더 맵으로 평탄화 (배열 제외) */
function flatten(obj, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'string') out[key] = md(v);
    else if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, out);
  }
  return out;
}

let html = template;

// 1) 단순 플레이스홀더 치환
const map = flatten(content);
for (const [key, val] of Object.entries(map)) {
  html = html.split(`{{${key}}}`).join(val);
}

// 2) 자동화 사다리 아이템
const ladderItems = content.ladder.items.map(it =>
  `    <div class="pl-step"><span class="pl-no">${md(it.no)}</span><span class="pl-ic">${md(it.icon)}</span><b>${md(it.name)}</b><small>${md(it.desc)}</small></div>`
).join('\n');
html = html.replace('{{LADDER_ITEMS}}', ladderItems);

// 3) 모듈 표 행
const moduleRows = content.modules.map(m => {
  const note = m.note ? ` <span class="sub">${md(m.note)}</span>` : '';
  return `    <tr><td>${md(m.name)}</td><td>${md(m.desc)}${note}</td><td>${md(m.ladder)}</td></tr>`;
}).join('\n');
html = html.replace('{{MODULE_ROWS}}', moduleRows);

// 4) fail-closed: 남은 플레이스홀더 검사
const leftovers = html.match(/\{\{[^}]+\}\}/g);
if (leftovers) {
  console.error('빌드 실패 — 미치환 플레이스홀더:', [...new Set(leftovers)].join(', '));
  process.exit(1);
}

writeFileSync(join(root, 'tutor.html'), html, 'utf8');
console.log(`OK — tutor.html 재생성 (${Buffer.byteLength(html, 'utf8')} bytes)`);
