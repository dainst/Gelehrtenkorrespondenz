from .crfutils import apply_templates


def feature_extractor(X, templates):
    # Apply attribute templates to obtain features (in fact, attributes)
    apply_templates(X, templates)
    if X:
        X[0]['F']['BOS'] = 'True'
        X[-1]['F']['EOS'] ='True'