import { mount } from "svelte";
import App from "./App.svelte";
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./app.css";

mount(App, { target: document.getElementById("app")! });
