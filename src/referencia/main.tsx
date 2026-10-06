import { render } from 'preact';
import { PaginaReferencia } from './PaginaReferencia';
import '../ui/estilos.css';
import './referencia.css';

const elementoRaiz = document.getElementById('referencia-app');
if (elementoRaiz) {
  render(<PaginaReferencia />, elementoRaiz);
}
