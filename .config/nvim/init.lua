vim.g.mapleader = " "
vim.g.maplocalleader = " "
vim.g.have_nerd_font = true
vim.opt.number = true
vim.opt.mouse = "a"
vim.opt.showmode = false
vim.opt.breakindent = true
vim.opt.undofile = true
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.signcolumn = "yes"
vim.opt.updatetime = 250
vim.opt.timeoutlen = 300
vim.opt.expandtab = true
vim.opt.tabstop = 2
vim.opt.softtabstop = 2
vim.opt.shiftwidth = 2
vim.opt.swapfile = false
vim.opt.list = true
vim.opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }
vim.opt.cursorline = true
vim.opt.scrolloff = 40
vim.opt.clipboard = "unnamedplus"
vim.opt.inccommand = "split"

-- highlight on copy
vim.api.nvim_create_autocmd("TextYankPost", {
	desc = "Highlight when yanking",
	group = vim.api.nvim_create_augroup("kickstart-highlight-yank", {clear = true}),
	callback = function()
		vim.highlight.on_yank()
	end,
})

-- keybinds for navigation
vim.keymap.set("n", "<leader>h", "<C-w><C-h>", {desc = "move focus to left"})
vim.keymap.set("n", "<leader>l", "<C-w><C-l>", {desc = "move focus to right"})
vim.keymap.set("n", "<leader>j", "<C-w><C-j>", {desc = "move focus to lower"})
vim.keymap.set("n", "<leader>k", "<C-w><C-k>", {desc = "move focus to upper"})

-- lazy nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
	vim.fn.system({
		"git",
		"clone",
		"--filter=blob:none",
		"https://github.com/folke/lazy.nvim.git",
		lazypath,
	})
end
vim.opt.rtp:prepend(lazypath)

--plugins
require("lazy").setup({

	-- Colorscheme
	{
		"rebelot/kanagawa.nvim",
		priority = 1000,
		config = function()
			vim.cmd.colorscheme("kanagawa-wave")
		end,
	},

	-- Treesitter 
	{
		"nvim-treesitter/nvim-treesitter",
    version ="v0.9.3",
		build = ":TSUpdate",
		lazy = false,
		config = function()
			require("nvim-treesitter.configs").setup({
				ensure_installed = {
					"diff",
					"luadoc",
					"markdown_inline",
					"query",
					"c",
					"lua",
					"vim",
					"javascript",
					"html",
					"markdown",
					"python",
					"bash",
				},
				auto_install = true,
				highlight = { enable = true },
				indent = { enable = true },
			})
		end,
	},

	-- Telescope
	{
		"nvim-telescope/telescope.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		config = function()
			local builtin = require("telescope.builtin")
			vim.keymap.set("n", "<leader>ff", builtin.find_files)
			vim.keymap.set("n", "<leader>fg", builtin.live_grep)
		end,
	},

	-- Neo-tree
	{
		"nvim-neo-tree/neo-tree.nvim",
		branch = "v3.x",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"MunifTanjim/nui.nvim",
		},
		config = function()
			require("neo-tree").setup({
				filesystem = {
					filtered_items = {
						visible = true,
						hide_dotfiles = false,
						hide_gitignored = false,
					},
				},
			})
			vim.keymap.set("n", "<leader>e", ":Neotree toggle<CR>")
		end,
	},


	-- CMP + Snippets
	{
		"hrsh7th/nvim-cmp",
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			"L3MON4D3/LuaSnip",
			"saadparwaiz1/cmp_luasnip",
		},
		config = function()
			local cmp = require("cmp")
			cmp.setup({
				snippet = {
					expand = function(args)
						require("luasnip").lsp_expand(args.body)
					end,
				},
				mapping = cmp.mapping.preset.insert({
					["<CR>"] = cmp.mapping.confirm({ select = true }),
				}),
				sources = {
					{ name = "nvim_lsp" },
					{ name = "luasnip" },
				},
			})
		end,
	},

	-- Lualine (SSH safe)
	{
		"nvim-lualine/lualine.nvim",
		config = function()
			require("lualine").setup({
				options = { icons_enabled = true },
			})
		end,
	},

	-- Indent guides
	{
		"lukas-reineke/indent-blankline.nvim",
		main = "ibl",
		config = true,
	},

	-- Formatter
	{
		"stevearc/conform.nvim",
		config = function()
			require("conform").setup({
				formatters_by_ft = { lua = { "stylua" } },
			})
		end,
	},

})

