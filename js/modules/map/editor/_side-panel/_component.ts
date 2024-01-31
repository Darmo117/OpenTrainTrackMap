export default interface Component {
  get container(): HTMLElement;

  get visible(): boolean;

  set visible(visible: boolean);
}
