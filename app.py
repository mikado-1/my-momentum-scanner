KeyError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/my-momentum-scanner/app.py", line 191, in <module>
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/metrics_util.py", line 532, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/arrow.py", line 725, in dataframe
    marshall_styler(proto.arrow_data, data, default_uuid)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/lib/pandas_styler_utils.py", line 65, in marshall_styler
    styler._compute()  # type: ignore
    ~~~~~~~~~~~~~~~^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/io/formats/style_render.py", line 256, in _compute
    r = func(self)(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/io/formats/style.py", line 1752, in _apply
    self._update_ctx(result)
    ~~~~~~~~~~~~~~~~^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/io/formats/style.py", line 1549, in _update_ctx
    raise KeyError(
    ...<2 lines>...
    )