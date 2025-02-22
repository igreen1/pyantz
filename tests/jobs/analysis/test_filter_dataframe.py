"""Test filtering a dataframe on a field"""

import pandas as pd
import logging
from pyantz.jobs.analysis.filter_dataframe import filter_dataframe

def test_filter_dataframe(tmpdir) -> None:

    data = pd.DataFrame({
        'a': [1,2,3],
        'b': [1.0, 2.1, 3.3],
        'c': ['a', 'b', 'c'],
        'd': [True, False, True]
    })

    # Save the data to a parquet file
    input_file = tmpdir.join("input.parquet")
    data.to_parquet(input_file)
    # Filter the data
    output_file = tmpdir.join("output.parquet")
    query = "a > 1"
    filter_dataframe(
        {
            "input_file": str(input_file),
            "query_string": query,
            "output_file": str(output_file)
        },
        logging.getLogger('test')
    )  
    # Read the filtered data
    filtered_data = pd.read_parquet(output_file)
    # Check that the output file is created
    assert output_file.check()
    # Check that the data is filtered correctly
    assert len(filtered_data) == 2
    assert filtered_data['a'].iloc[0] == 2
    assert filtered_data['a'].iloc[1] == 3
    assert filtered_data['b'].iloc[0] == 2.1
    assert filtered_data['b'].iloc[1] == 3.3
    assert filtered_data['c'].iloc[0] == 'b'
    assert filtered_data['c'].iloc[1] == 'c'
    assert filtered_data['d'].iloc[0] == False
    assert filtered_data['d'].iloc[1] == True