import os
from argparse import ArgumentParser

import cv2

from mmpose.apis import (get_track_id, inference_bottom_up_pose_model,
                         init_pose_model, vis_pose_tracking_result)


def main():
    """Visualize the demo images."""
    parser = ArgumentParser()
    parser.add_argument('pose_config', help='Config file for pose')
    parser.add_argument('pose_checkpoint', help='Checkpoint file for pose')
    parser.add_argument('--video-path', type=str, help='Video path')
    parser.add_argument(
        '--show',
        action='store_true',
        default=False,
        help='whether to show visualizations.')
    parser.add_argument(
        '--out-video-root',
        default='',
        help='Root of the output video file. '
        'Default not saving the visualization video.')
    parser.add_argument(
        '--device', default='cuda:0', help='Device used for inference')
    parser.add_argument(
        '--kpt-thr', type=float, default=0.5, help='Keypoint score threshold')
    parser.add_argument(
        '--iou-thr', type=float, default=0.3, help='IoU score threshold')
    parser.add_argument(
        '--oks-thr', type=float, default=0.3, help='OKS score threshlod')
    parser.add_argument(
        '--oks', action='store_true', default=False, help='Using OKS tracking')
    parser.add_argument(
        '--euro',
        action='store_true',
        default=False,
        help='Using One_Euro_Filter for smoothing')

    args = parser.parse_args()

    assert args.show or (args.out_video_root != '')

    # build the pose model from a config file and a checkpoint file
    pose_model = init_pose_model(
        args.pose_config, args.pose_checkpoint, device=args.device.lower())

    dataset = pose_model.cfg.data['test']['type']
    assert (dataset == 'BottomUpCocoDataset')

    cap = cv2.VideoCapture(args.video_path)
    fps = None

    assert cap.isOpened(), f'Faild to load video file {args.video_path}'

    if args.out_video_root == '':
        save_out_video = False
    else:
        os.makedirs(args.out_video_root, exist_ok=True)
        save_out_video = True

    if save_out_video:
        fps = cap.get(cv2.CAP_PROP_FPS)
        size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        videoWriter = cv2.VideoWriter(
            os.path.join(args.out_video_root,
                         f'vis_{os.path.basename(args.video_path)}'), fourcc,
            fps, size)

    # optional
    return_heatmap = False

    # e.g. use ('backbone', ) to return backbone feature
    output_layer_names = None
    next_id = 0
    pose_results = []
    while (cap.isOpened()):
        flag, img = cap.read()
        if not flag:
            break
        pose_results_last = pose_results

        pose_results, returned_outputs = inference_bottom_up_pose_model(
            pose_model,
            img,
            return_heatmap=return_heatmap,
            outputs=output_layer_names)

        # get track id for each person instance
        pose_results, next_id = get_track_id(
            pose_results,
            pose_results_last,
            next_id,
            iou_thr=args.iou_thr,
            oks_thr=args.oks_thr,
            use_oks=args.oks,
            use_one_euro=args.euro,
            fps=fps)

        # show the results
        vis_img = vis_pose_tracking_result(
            pose_model,
            img,
            pose_results,
            dataset=dataset,
            kpt_score_thr=args.kpt_thr,
            show=False)

        if args.show:
            cv2.imshow('Image', vis_img)

        if save_out_video:
            videoWriter.write(vis_img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if save_out_video:
        videoWriter.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
