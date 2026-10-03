import { render } from 'preact';
import { App } from './app';
import './ui/estilos.css';

render(<App />, document.getElementById('app') as HTMLElement);
