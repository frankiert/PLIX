"""
Class that classifies texts from a dataframe.
"""
import plix.helpers.common_functions as cf
import plix.nlp_assets as nlp_assets


def classify_texts(df):
    """
    Method to classify text in a pd.DataFrame object given the class labels in `nlp_assets`.

    :param pd.DataFrame df: dataframe from the data extraction

    :returns: dataframe with added Classification and classification count columns
    :rtype: pd.DataFrame
    """
    df['Classification'], df['ClassificationCount'] = __do_text_classification(df)
    df = cf.reorder_columns(df, ['Filename',
                                 'FullPath',
                                 'Category',
                                 'Classification',
                                 'ClassificationCount',
                                 'TableData',
                                 'Metadata',
                                 'allText',
                                 'cleanText',
                                 'MeaningfulText',
                                 'Text',
                                 'cleanOCRText',
                                 'OCRedText'
                                 ])
    return df


def __do_text_classification(df):
    result = []
    count_res = []
    texts = df['allText']
    files = df['Filename']
    for i, (t, f) in enumerate(zip(texts, files)):
        cf.log('Classifying ' + f)
        # include file name ( = title) since it is not extracted sometimes
        text = f + ' ' + t
        found_classes = []
        count = [0] * len(nlp_assets.TEXT_CLASSES)
        for j, c in enumerate(nlp_assets.TEXT_CLASSES):
            for synonym in c:
                syn_count = text.lower().count(synonym.lower())
                if syn_count > 0:
                    found_classes.append(c[0])
                    count[j] += syn_count
        result.append(found_classes)
        count_res.append(count)
    return result, count_res
