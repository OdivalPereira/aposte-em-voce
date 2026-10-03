// PDF mínimo com senha (AES-256, revisão 5 do manipulador padrão), para provar o caminho da senha de ponta a ponta.
// A pdf-lib não sabe cifrar; aqui o PDF é escrito à mão, com o texto nas posições dadas (dados fictícios).
import { createCipheriv, createHash, randomBytes } from 'node:crypto';
import type { PaginaTexto } from '../../../src/leitura/tipos';

const sha256 = (...partes: Buffer[]) => createHash('sha256').update(Buffer.concat(partes)).digest();

function aesSemPreenchimento(chave: Buffer, dados: Buffer): Buffer {
  const c = createCipheriv('aes-256-cbc', chave, Buffer.alloc(16));
  c.setAutoPadding(false);
  return Buffer.concat([c.update(dados), c.final()]);
}

function cifrarStream(chave: Buffer, dados: Buffer): Buffer {
  const iv = randomBytes(16);
  const c = createCipheriv('aes-256-cbc', chave, iv);
  return Buffer.concat([iv, c.update(dados), c.final()]);
}

const hex = (b: Buffer) => `<${b.toString('hex')}>`;
const escapar = (t: string) => t.replace(/[\\()]/g, (m) => `\\${m}`);

export function gerarPdfComSenha(paginas: PaginaTexto[], senha: string): Uint8Array {
  const chaveArquivo = randomBytes(32);
  const senhaB = Buffer.from(senha, 'utf8');
  const valSalt = randomBytes(8);
  const keySalt = randomBytes(8);
  const U = Buffer.concat([sha256(senhaB, valSalt), valSalt, keySalt]);
  const UE = aesSemPreenchimento(sha256(senhaB, keySalt), chaveArquivo);
  const ovSalt = randomBytes(8);
  const okSalt = randomBytes(8);
  const dono = Buffer.from(`${senha}-dono`, 'utf8');
  const O = Buffer.concat([sha256(dono, ovSalt, U), ovSalt, okSalt]);
  const OE = aesSemPreenchimento(sha256(dono, okSalt, U), chaveArquivo);
  const perms = Buffer.concat([Buffer.from([0xfc, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x54, 0x61, 0x64, 0x62]), randomBytes(4)]);
  const ecb = createCipheriv('aes-256-ecb', chaveArquivo, null);
  ecb.setAutoPadding(false);
  const Perms = Buffer.concat([ecb.update(perms), ecb.final()]);

  // Objetos: 1 catálogo, 2 páginas, 3 fonte, 4 cifra, depois (página, conteúdo) por página.
  const n = paginas.length;
  const corpos: Buffer[] = [];
  const texto = (s: string) => Buffer.from(s, 'latin1');
  corpos[1] = texto('<< /Type /Catalog /Pages 2 0 R >>');
  corpos[2] = texto(`<< /Type /Pages /Count ${n} /Kids [${paginas.map((_, i) => `${5 + 2 * i} 0 R`).join(' ')}] >>`);
  corpos[3] = texto('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>');
  corpos[4] = texto(
    `<< /Filter /Standard /V 5 /R 5 /Length 256 /P -4 /EncryptMetadata true /CF << /StdCF << /AuthEvent /DocOpen /CFM /AESV3 /Length 32 >> >> /StmF /StdCF /StrF /StdCF /O ${hex(O)} /U ${hex(U)} /OE ${hex(OE)} /UE ${hex(UE)} /Perms ${hex(Perms)} >>`,
  );
  paginas.forEach((p, i) => {
    corpos[5 + 2 * i] = texto(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents ${6 + 2 * i} 0 R >>`);
    const conteudo = p.itens.map((it) => `BT /F1 8 Tf ${it.x} ${it.y} Td (${escapar(it.texto)}) Tj ET`).join('\n');
    const cifrado = cifrarStream(chaveArquivo, Buffer.from(conteudo, 'latin1'));
    corpos[6 + 2 * i] = Buffer.concat([texto(`<< /Length ${cifrado.length} >>\nstream\n`), cifrado, texto('\nendstream')]);
  });

  const partes: Buffer[] = [texto('%PDF-1.7\n')];
  const posicoes: number[] = [];
  let tamanho = partes[0]?.length ?? 0;
  for (let id = 1; id < corpos.length; id++) {
    posicoes[id] = tamanho;
    const obj = Buffer.concat([texto(`${id} 0 obj\n`), corpos[id] as Buffer, texto('\nendobj\n')]);
    partes.push(obj);
    tamanho += obj.length;
  }
  const total = corpos.length;
  const xref = [`xref\n0 ${total}\n0000000000 65535 f \n`, ...posicoes.slice(1).map((o) => `${String(o).padStart(10, '0')} 00000 n \n`)].join('');
  const id = hex(randomBytes(16));
  partes.push(texto(`${xref}trailer\n<< /Size ${total} /Root 1 0 R /Encrypt 4 0 R /ID [${id} ${id}] >>\nstartxref\n${tamanho}\n%%EOF\n`));
  return new Uint8Array(Buffer.concat(partes));
}
