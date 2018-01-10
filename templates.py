

template1 = (
    # sent rank
    (("sent_rank", 0), ),
    # token rank
    (('rank', 0), ),
    # token
    (('w', -2), ),
    (('w', -1), ),
    (('w',  0), ),
    (('w',  1), ),
    (('w',  2), ),
    (('w', -1), ('w',  0)),
    ( ('w',  0), ('w',  1)),
    # word-lower case
    (('w_lower', 0), ),
    (('w_lower', -1), ),
    (('w_lower', -2), ),
    (('w_lower', 1), ),
    (('w_lower', 2), ),
    # pos
    (('pos', -2), ),
    (('pos', -1), ),
    (('pos',  0), ),
    (('pos',  1), ),
    (('pos',  2), ),
    (('pos', -2), ('pos', -1) ),
    (('pos', -1), ('pos',  0) ),
    (('pos',  0), ('pos',  1) ),
    (('pos',  1), ('pos',  2) ),
    (('pos', -2), ('pos', -1), ('pos',  0) ),
    (('pos', -1), ('pos',  0), ('pos',  1) ),
    (('pos',  0), ('pos',  1), ('pos',  2) ),
    # lemma
    (('lemma', 0), ),
    (('lemma', -1), ),
    (('lemma', +1), ),
    # is uppercase
    (('isUpper', 0), ),
    (('isUpper', -1), ),
    (('isUpper', +1), ),
    # is titlecase
    (('isTitle', 0), ),
    (('isTitle', -1), ),
    (('isTitle', +1), ),
    # is digit
    (('isDigit', 0), ),
    (('isDigit', -1), ),
    (('isDigit', +1), ),
    # has digit
    (('hasDigit', 0), ),
    (('hasDigit', -1), ),
    (('hasDigit', +1), ),
    # ends with digit
    (('endsWithDigit', 0), ),
    (('endsWithDigit', -1), ),
    (('endsWithDigit', +1), ),
    # prefix (long)
    (('prefix_long', 0), ),
    (('prefix_long', -1), ),
    (('prefix_long', -2), ),
    (('prefix_long', +1), ),
    (('prefix_long', +2), ),
    # prefix (short)
    (('prefix_short', 0), ),
    (('prefix_short', -1), ),
    (('prefix_short', -2), ),
    (('prefix_short', +1), ) ,
    (('prefix_short', +2), ),
    # suffix (long)
    (('suffix_long', 0), ),
    (('suffix_long', -1), ),
    (('suffix_long', -2), ),
    (('suffix_long', +1), ),
    (('suffix_long', +2),) ,
    (('suffix_long', -1), ('suffix_long',  0)),
    (('suffix_long', 0), ('suffix_long',  +1)),
    (('suffix_long',  0), ('suffix_long',  1), ('suffix_long',  2) ),
    (('suffix_long',  -2), ('suffix_long',  -1), ('suffix_long',  0) ),
    # suffix (short)
    (('suffix_short', 0), ),
    (('suffix_short', -1), ),
    (('suffix_short', -2), ),
    (('suffix_short', +1), ),
    (('suffix_short', +2), ),
    (('suffix_short', -1), ('suffix_short', 0)),
    (('suffix_short', 0), ('suffix_short', +1)),
    (('suffix_short',  0), ('suffix_short',  1), ('suffix_short',  2) ),
    (('suffix_short',  -2), ('suffix_short',  -1), ('suffix_short',  0) ),
    # person dictionary
    (('isInPersonDic', 0), ),
    (('isInPersonDic', -1), ),
    (('isInPersonDic', -2), ),
    (('isInPersonDic', +1), ),
    (('isInPersonDic', +2), ),
    #(('isInPersonDic', -1), ('isInPersonDic', 0)),
    #(('isInPersonDic', 0), ('isInPersonDic', +1)),
    # place dictionary
    (('isInPlaceDic', 0), ),
    (('isInPlaceDic', -1), ),
    (('isInPlaceDic', -2), ),
    (('isInPlaceDic', +1), ),
    (('isInPlaceDic', +2), ),
    #(('isInPlaceDic', -1), ('isInPlaceDic', 0)),
    #(('isInPlaceDic', 0), ('isInPlaceDic', +1)),
)