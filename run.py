import gc, pickle, torch, os, argparse, sys
import ptp_utils, seq_aligner


from tqdm import tqdm
from diffusers import  DiffusionPipeline, DDIMScheduler
from null import NullInversion
from local import AttentionStore, show_cross_attention, run_and_display, make_controller




def main(args):

    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    scheduler = DDIMScheduler(beta_start=0.00085, beta_end=0.012, beta_schedule="scaled_linear", clip_sample=False, set_alpha_to_one=False)
    model = "stabilityai/stable-diffusion-xl-base-1.0"
    DISN = DiffusionPipeline.from_pretrained(
            model,
            scheduler=scheduler,
            torch_dtype=torch.float32,
        ).to(device)
    
    
    pjf_path = "./lora"
    DISN.load_lora_weights(pjf_path, weight_name="pytorch_lora_weights.safetensors")
    DISN.disable_xformers_memory_efficient_attention()
    DISN.enable_model_cpu_offload()

    null_inversion = NullInversion(DISN)

    
    image_path = args.original_dataset_path
    directory = args.new_dataset_path
    prompt = args.prompt
    neg_prompt = args.neg_prompt
    
    
    extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    image_files = [os.path.join(dirpath, filename)
                for dirpath, dirnames, filenames in os.walk(image_path)
                for filename in filenames
                if filename.lower().endswith(extensions)]

    
    
    
    print("🌊 pos_prompt = ", prompt)
    print("🌊 net_prompt = ", neg_prompt)
    prompts = [prompt, prompt]
    neg_prompts =  [neg_prompt, neg_prompt]
    
    bar = tqdm(total=len(image_files))
    
    
    
    for i, file_path in enumerate(image_files):   
        file_name = file_path.split("/")[-1]
        bar.set_description(f"Creating {i}/{len(image_files)}-th {file_name}")
        (image_gt, image_enc), x_t, uncond_embeddings, uncond_embeddings_p = null_inversion.invert(file_path, prompt, verbose=True, do_1024=args.bigger)  
        torch.cuda.empty_cache()
        gc.collect()

        
        controller = AttentionStore()
        image_inv, x_t = run_and_display(DISN,neg_prompts,prompts, controller, run_baseline=False, latent=x_t, uncond_embeddings=uncond_embeddings, uncond_embeddings_p=uncond_embeddings_p,verbose=False)
        ptp_utils.make_dataset([image_gt, image_enc, image_inv[0]],directory, file_name)
        torch.cuda.empty_cache()
        gc.collect()
        
        bar.set_description(f"Creating {i}/{len(image_files)}-th {file_name}")
        bar.update()
        



if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("--original_dataset_path", type=str, default="./original_dataset", help="Existing Data Paths") 
    p.add_argument("--new_dataset_path", type=str, default="./new_dataset", help="The path of the new image to be saved")  
    p.add_argument("--prompt", type=str, default="photo of a crack defect image", help="Positive Prompt")  
    p.add_argument("--neg_prompt", type=str, default="", help="Negative Prompt")  
    p.add_argument("--bigger", action='store_true', help="If you want to create an image 1024")
  
  
  
    args = p.parse_args()
    
    if not os.path.exists(args.original_dataset_path):
        print(f"Error: The directory '{args.original_dataset_path}' does not exist.")
        sys.exit(1)  
        
    if not os.path.exists(args.new_dataset_path):
        os.makedirs(args.new_dataset_path, exist_ok=True)
        print(f"Directory '{args.new_dataset_path}' was created.")
    
    main(args)
  





