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

## Prepare Your Test

To setup and run your test, you need to properly prepare your test. Here is a step-by-step guide for this.

### 1. Prepare your samples

Gather all samples from all the systems you would like to evaluate, and move them under a certain root directory. For example:
```
Top level directory
- Prompt_Speech_for_TTS
- Groundtruth_Target_Speech_for_TTS
- TTS_System_1
- TTS_System_2
...
```

### 2. Build the Test List

*Test List* is an input JSON file for the Gradio MOS Test suite. An example of it can be found [here](https://github.com/aalto-speech/Gradio_MOS_template/blob/main/test_lists/example.json). The outer keys of the *Test List* are the tests you would like to run, and the corresponding value of the key is a list of lists of object. The nested lists contain all possible test cases you would like to have for one system in this test.

```json
{
    "CMOS": [ //outer list, a collection of all test cases of all systems in this test type
        [ // inner list, all test cases of one system in this test type
            { // 1 testcase
                ...
            },
            ...
        ],
        ...
    ],
    ...
}
```

To create such *Test List*, you can refer to one of the example under `test_list_builders`, for example the local filesystem [one](https://github.com/aalto-speech/Gradio_MOS_template/blob/main/test_list_builders/local_fs/generate.py) and its corresponding [configs](https://github.com/aalto-speech/Gradio_MOS_template/tree/main/test_list_builders/local_fs/config). It can be run as:
```bash
uv run test_list_builders/local_fs/generate.py \
    --config_name finnish \ # One of the config name under the test_list_builders config path
    output="YOUR_OUTPUT_DIR" \
    root_dir="ROOT_DIR_FOR_ALL_SYSTEM_SAMPLES"
```

We also have `test_list_builder` for Gdrive or web file server for your reference. Of course, you can create your own `test_list_builder` depending on your case.

### Run Your Test

With *Test List* prepared, you can run your test now:
```bash
uv run main.py --config-name CONFIG_NAME # The config name under the `config` path at the root of this project.
```

## Extend different types of test page

The general idea of extending to more test type is to add the new type of page as a subclass of the `TestPage` object and implement the corresponding methods. Then you need to register your new page class at the `PageFactory`. In this way, your new test page will be built automatically when you pass the test type and other metadata to the `MOSTest` in `main.py`.

Please refer to `pages` folder for more details.

## Future Plans

- [ ] Provide support for different methods on obtaining `self.test_cases`
- [ ] Supporting more types of test