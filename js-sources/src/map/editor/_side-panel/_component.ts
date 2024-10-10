export default abstract class Component {
  abstract get container(): JQuery;

  abstract get visible(): boolean;

  abstract set visible(visible: boolean);
}
