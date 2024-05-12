import gc, pickle, torch, argparse, os, sys
import ptp_utils, seq_aligner

from diffusers import  DiffusionPipeline, DDIMScheduler
from null import NullInversion
from local import AttentionStore, show_cross_attention, run_and_display, make_controller




# CUDA_VISIBLE_DEVICES=4 python run.py



def main(args):
    
    prompt = args.prompt
    neg_prompt = args.neg_prompt
    image_path = args.image_path
    

    ###################################### DISN
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

    ###################################### DISN

    null_inversion = NullInversion(DISN)
    (image_gt, image_enc), x_t, uncond_embeddings, uncond_embeddings_p = null_inversion.invert(image_path, prompt, verbose=True, do_1024=args.bigger)
    torch.cuda.empty_cache()
    gc.collect()
    
    prompts = [prompt, prompt]
    controller = AttentionStore()
    neg_prompts =  [neg_prompt, neg_prompt]

    image_inv, x_t = run_and_display(DISN,neg_prompts,prompts, controller, run_baseline=False, latent=x_t, uncond_embeddings=uncond_embeddings, uncond_embeddings_p=uncond_embeddings_p,verbose=False)
    ptp_utils.view_images([image_gt, image_enc, image_inv[0]])
    ptp_utils.save_individual_images([image_gt, image_enc, image_inv[0]])
    show_cross_attention(DISN,prompts,controller, 32, ["up","down","mid"])




    ###################################### Various Defect Generation 

    prompts = ["photo of a crack defect image",
            "photo of a crack corrosion image"]
    neg_prompts = [neg_prompt, neg_prompt] 

    cross_replace_steps = {'default_':1.0,}
    self_replace_steps = 0.4
    blend_word = ((('defect',), ("corrosion",))) 
    eq_params = {"words": ("corrosion",), "values": (2,)} # amplify attention to the word "red" by *2


    controller = make_controller(DISN,prompts, True, cross_replace_steps, self_replace_steps, blend_word, eq_params, blend_word)
    images, _ = run_and_display(DISN,neg_prompts, prompts, controller, run_baseline=False, latent=x_t, uncond_embeddings=uncond_embeddings,uncond_embeddings_p=uncond_embeddings_p, steps=50)




if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument("--image_path", type=str, default="./img/[0001]TopBF0.png", help="Image Path") 
    p.add_argument("--prompt", type=str, default="photo of a crack defect image", help="Positive Prompt")  
    p.add_argument("--neg_prompt", type=str, default="", help="Negative Prompt")  
    p.add_argument("--bigger", action='store_true', help="If you want to create an image 1024")
  
    args = p.parse_args()

    
    main(args)
  


