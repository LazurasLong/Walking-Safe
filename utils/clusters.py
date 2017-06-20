import argparse
import logging
import os

import numpy as np
import pandas as pd
from pandas import DataFrame
from pandas import Series
from scipy.spatial.distance import euclidean
from sklearn.cluster import KMeans


def set_logger():
    """Setup of stream log for quick debug"""

    logger = logging.getLogger('clusters')
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh.setFormatter(formatter)
    logger.addHandler(sh)

def assign_label(x, centers):
    """Assign lable to X, based on cluster centers"""

    min = np.inf
    label = None
    for l, v in centers.items():
        dist = euclidean(x, v)
        if min > dist:
            min = dist
            label = l
    return l

def get_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, help='path to JSON crime data file')
    parser.add_argument('--clusters', type=int, help='number of clusters', default=10)
    args = parser.parse_args()
    file = args.file
    clusters = args.clusters
    return file, clusters

def main():

    set_logger()
    logger = logging.getLogger('clusters.main')
    logger.info("Parsing arguments")
    file, clusters = get_args()
    logger.info("Performing KMeans clustering")
    df = pd.read_json(file)
    X = df.loc[:, ['lat', 'lng']].values
    kmeans = KMeans(n_clusters=clusters, max_iter=1000).fit(X)

    #Cluster metadata
    centers = {k: v for k, v in enumerate(kmeans.cluster_centers_)}
    logger.info("Counting number of crimes of each cluster")
    labels = Series(kmeans.labels_)
    num_labels = {}
    for l in labels.unique():
        num = labels[labels == l].count()
        num_labels[l] = num
    logger.debug("number of occurrences of each label: {}".format(num_labels))

    logger.info("Transofrming counting into percentage")
    total = labels.count()
    percentage = {k: v/total for k, v in num_labels.items()}
    logger.debug("percentage of each label: {}".format(percentage))

    logger.info("Removing clusters with few points")
    labels_remove = []
    for l, v in percentage.items():
        if v < 0.1:
            idx = (labels == l)
            lost_p = X[idx]
            try:
                lost_points = np.concatenate((lost_points, lost_p), axis=0)
            except NameError:
                lost_points = lost_p
            labels_remove.append(l)
    #Remove labels from other data structures
    for l in labels_remove:
        percentage.pop(l, 'None')
        num_labels.pop(l, 'None')
        centers.pop(l, 'None')

    logger.debug("number of occurrences of each label after filtering: {}".format(num_labels))
    logger.debug("percentage of each label after filtering: {}".format(percentage))
    logger.debug("Number of filtered points: {}".format(lost_points.shape[0]))

    logger.info("Assign lost points to new clusters")
    new_labels = np.apply_along_axis(
        lambda x: assign_label(x, centers),
        axis=1,
        arr=lost_points)
    #Update data structures
    for l in new_labels:
        num_labels[l] += 1
    percentage = {k: v/total for k, v in num_labels.items()}

    logger.info("Save results in JSON")
    #Clusters
    columns = ['lat', 'lng']
    df_clusters = DataFrame(centers, columns=columns)
    _, new_file = os.path.split(file)
    new_file, _ = os.path.splitext(new_file)
    df_clusters.to_json(
        path_or_buf=new_file+'Cluster.json',
        orient='records'
    )
    #Metadata
    columns = [
        'Number of crimes',
        'Percentage of total crimes',
        'Coordinates'
        ]
    df_meta = DataFrame({
        columns[0]: num_labels,
        columns[1]: percentage,
        columns[2]: centers
    })
    df_meta.to_json(
        path_or_buf=new_file+'ClusterMeta.json',
        orient='records'
    )

main()
