# Gradio_MOS_template

The is a template for using [Gradio](https://www.gradio.app/) to conduct Mean Opinion Score (MOS) evaluation for Speech and Audio Generation.

## Setup environment

We use [uv](https://github.com/astral-sh/uv) for dependency management. Please follow the instruction to install **uv** first.

Then install the dependencies via:
```bash
uv sync
```

## Run locally
Run the following command:
```bash
uv run main.py --config-name CONFIG_NAME [other_overwriting_arguments]
```

## Extend different types of test page

The general idea of extending to more test type is to add the new type of page as a subclass of the `TestPage` object and implement the corresponding methods. Then you need to register your new page class at the `PageFactory`. In this way, your new test page will be built automatically when you pass the test type and other metadata to the `MOSTest` in `main.py`.

Please refer to `pages` folder for more details.

## Future Plans

- [ ] Provide support for different methods on obtaining `self.test_cases`
- [ ] Supporting more types of test