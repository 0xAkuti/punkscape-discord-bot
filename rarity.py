from collections import Counter


def add_rarity_info(data):
    # collect unique trait types
    trait_types = set()
    for ps in data.values():
        for attr in ps['attributes']:
            trait_types.add(attr['trait_type'])
    trait_types.remove('date')  # as every scape has that
    # add missing trait types
    for id in data:
        ps = data[id]
        missing_traits = trait_types - set([a['trait_type'] for a in ps['attributes']])
        for trait in missing_traits:
            ps['attributes'].append({'value': 'None', 'trait_type': trait})
    # caculate trait occurences and rarity scores
    attrs = [attr for ps in data.values() for attr in ps['attributes']]
    attrr_counter = Counter([f"{attr['trait_type']}: {attr['value']}" for attr in attrs
                             if attr['trait_type'] != 'date'])
    attr_occurences = {k: v for k, v in attrr_counter.most_common()}
    attr_count_rarity_scores = {k: round(1/(v / len(data)), 2)
                                for k, v in Counter(ps['attribute_count'] for ps in data.values()).most_common()}
    attr_rarity_scores = {k: round(1/(count / len(data)), 2) for k, count in attr_occurences.items()}
    ps_rarity_scores = {}
    # add rarity data
    for id in data:
        ps = data[id]
        attr_scores = {
            f"{attr['trait_type']}: {attr['value']}": attr_rarity_scores[f"{attr['trait_type']}: {attr['value']}"]
            for attr in ps['attributes'] if attr['trait_type'] != 'date'}
        attr_scores[f"Attribute Count: {ps['attribute_count']}"] = attr_count_rarity_scores[ps['attribute_count']]
        ps['rarity_score'] = round(sum(attr_scores.values()), 2)
        ps['attributes_rarity_scores'] = attr_scores
        for attr in ps['attributes']:
            if attr['trait_type'] == 'date':
                ps['date'] = attr['value']
                break
        ps_rarity_scores[id] = ps['rarity_score']
    # add ranking
    ranking = [id for id, _ in sorted(list(ps_rarity_scores.items()), key=lambda x: -x[1])]
    for id in data:
        data[id]['rank'] = ranking.index(id)
