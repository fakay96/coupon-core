function main(splash, args)
        -- Configure viewport and timeout
        splash:set_viewport_size(1920, 1080)
        splash.private_mode_enabled = false
        splash:set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        -- Go to URL and wait for initial load
        assert(splash:go(args.url))
        assert(splash:wait(3))
        
        -- Handle cookie consent
        local consent_button = splash:select('button[data-testid="uc-accept-all-button"]')
        if consent_button then
            consent_button:mouse_click()
            splash:wait(2)
        end
        
        -- Scroll simulation for dynamic loading
        for i = 1, 6 do
            splash:evaljs("window.scrollTo(0, document.body.scrollHeight * " .. i .. "/6)")
            splash:wait(1)
        end
        
        -- Final wait for all content to load
        splash:wait(2)
        
        -- Get next page button status
        local next_button = splash:select('button.pagination__btn--next')
        local has_next = next_button ~= nil and not next_button:hasClass('disabled')
        
        -- Click next if requested
        if args.click_next and has_next then
            next_button:mouse_click()
            splash:wait(3)
            
            -- Scroll new page
            for i = 1, 6 do
                splash:evaljs("window.scrollTo(0, document.body.scrollHeight * " .. i .. "/6)")
                splash:wait(1)
            end
        end
        
        return {
            html = splash:html(),
            has_next = has_next,
            cookies = splash:get_cookies(),
            url = splash:url()
        }
    end
