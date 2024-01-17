import * as st from "../modules/streams";

function array(size: number): number[] {
  return new Array(size).fill(1);
}

let array1 = array(1e6);
let stream = st.stream(array(1e6));

let start = new Date().getTime();
for (let i = 0; i < 100; i++) {
  array1 = array1.map(e => e + 1);
}
array1.forEach(() => {
});
console.log(new Date().getTime() - start);

start = new Date().getTime();
for (let i = 0; i < 100; i++) {
  stream = stream.map(e => e + 1);
}
stream.forEach(() => {
});
console.log(new Date().getTime() - start);
